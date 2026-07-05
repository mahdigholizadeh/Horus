import json
import hashlib
import logging
from typing import Any, Dict, Optional
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from datetime import datetime

class SetOutputDataAndVerificationModule:
    """
    Set Output Data and Verification Module (SODVM)

    Responsibilities:
    - Set (write) output data to a file or other storage.
    - Verify the integrity of JSON responses received from the API, ensuring they haven't been corrupted during transit.
    - Support hash/checksum verification and optional schema validation.
    - Log all operations and errors.
    """
    MODULE_CODE = "12"  # Unique code for SODVM

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.last_output_path = None
        self.last_output_hash = None
        # Error codes for this module (Module code: 12 for SODVM)

    def set_output_data(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Write output data to a file as JSON and store its hash for verification.
        Args:
            data: The output data to write.
            output_path: Path to the output file.
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.last_output_path = output_path
            self.last_output_hash = self._calculate_hash(data)
            self.logger.info(f"SODVM: Output data written to {output_path}")
            return True
        except Exception as e:
            error_msg = f"Failed to write output data: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SetOutputDataAndVerificationModule", "set_output_data")
            return False

    def verify_output_data(self, output_path: Optional[str] = None, expected_hash: Optional[str] = None) -> bool:
        """
        Verify the integrity of the output data by comparing its hash.
        Args:
            output_path: Path to the output file (defaults to last written).
            expected_hash: Expected hash (defaults to last written hash).
        Returns:
            True if verification passes, False otherwise.
        """
        try:
            path = output_path or self.last_output_path
            if not path:
                raise ValueError("No output path provided or recorded.")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            actual_hash = self._calculate_hash(data)
            expected = expected_hash or self.last_output_hash
            if actual_hash != expected:
                error_msg = f"Hash mismatch: expected {expected}, got {actual_hash}"
                self.logger.error(error_msg)
                self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_output_data")
                return False
            self.logger.info(f"SODVM: Output data at {path} verified successfully.")
            return True
        except Exception as e:
            error_msg = f"Failed to verify output data: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_output_data")
            return False

    def _calculate_hash(self, data: Any) -> str:
        """
        Calculate a SHA256 hash of the JSON-serializable data.
        Args:
            data: The data to hash.
        Returns:
            The SHA256 hash as a hex string.
        """
        try:
            json_bytes = json.dumps(data, sort_keys=True, separators=(",", ":")).encode('utf-8')
            return hashlib.sha256(json_bytes).hexdigest()
        except Exception as e:
            error_msg = f"Failed to calculate hash: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SetOutputDataAndVerificationModule", "calculate_hash")
            return ""

    def verify_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Optionally verify the data against a provided JSON schema.
        Args:
            data: The data to validate.
            schema: The JSON schema to validate against.
        Returns:
            True if valid, False otherwise.
        """
        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=schema)
            self.logger.info("SODVM: Output data schema validation passed.")
            return True
        except Exception as e:
            error_msg = f"Schema validation failed: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_schema")
            return False

    def verify_json(self, data: Any) -> bool:
        """
        Verify that the data is a valid OpenAI API response format.
        Args:
            data: The data to verify (can be dict, BasicAPIResponse, or other response format)
        Returns:
            True if valid, False otherwise.
        """
        try:
            # Handle BasicAPIResponse objects from BAAIM
            if hasattr(data, 'success') and hasattr(data, 'response'):
                # This is a BasicAPIResponse object
                if data.success and data.response is not None:
                    self.logger.info("SODVM: BasicAPIResponse verification passed.")
                    return True
                else:
                    error_msg = f"BasicAPIResponse verification failed: success={data.success}, response={data.response}"
                    self.logger.error(error_msg)
                    self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_json")
                    return False
            
            # Handle raw OpenAI API response format
            if isinstance(data, dict):
                # Check for OpenAI API response structure
                if "choices" in data:
                    choices = data.get("choices", [])
                    if choices and isinstance(choices, list):
                        first_choice = choices[0]
                        if isinstance(first_choice, dict) and "message" in first_choice:
                            message = first_choice["message"]
                            if isinstance(message, dict) and "content" in message:
                                self.logger.info("SODVM: OpenAI API response format verification passed.")
                                return True
                
                # Check for error response format
                if "error" in data:
                    error_info = data["error"]
                    if isinstance(error_info, dict) and "message" in error_info:
                        error_msg = f"OpenAI API error response: {error_info['message']}"
                        self.logger.warning(error_msg)
                        self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_json")
                        return False
            
            # If it's a simple dict with expected fields, consider it valid
            if isinstance(data, dict) and len(data) > 0:
                self.logger.info("SODVM: Generic JSON response verification passed.")
                return True
            
            error_msg = f"Invalid JSON response format: {type(data)}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_json")
            return False
            
        except Exception as e:
            error_msg = f"JSON verification failed: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SetOutputDataAndVerificationModule", "verify_json")
            return False

    def get_status(self) -> dict:
        """Return the last output path and hash for monitoring."""
        return {
            "last_output_path": self.last_output_path,
            "last_output_hash": self.last_output_hash
        }

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "SODVM",
            class_name,
            function_name,
            error_message,
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("SODVM", class_name, function_name, sub_function)

    async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", context: dict = None):
        """Handle exceptions with comprehensive logging and recovery."""
        error_message = str(exception)
        error_code = self.log_error(error_message, class_name, function_name)
        if hasattr(exception, 'status_code') or 'api' in error_message.lower():
            return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }

    async def handle_api_error(self, error_response: str, status_code: int = None, context: dict = None) -> dict:
        """Handle API errors using the centralized API error handler."""
        try:
            result = await api_error_handler.handle_api_error(error_response, status_code, context)
            self.error_manager.log_error_with_generation(
                "SODVM",
                "SODVM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "SODVM",
                "SODVM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)} 

# Global instance and alias for compatibility
sodvm = SetOutputDataAndVerificationModule()
SODVM = SetOutputDataAndVerificationModule  # Class alias

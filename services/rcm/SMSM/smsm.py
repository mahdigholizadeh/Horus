"""
System Message Subjoin Module (SMSM)

Allows the CCU to intervene in a conversation by injecting a system-level message.
Receives a message and Request ID from the CCU, then edits the conversation history to include the new message.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import DCMM for database operations
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from DCMM.dcmm import DatabaseControlAndManagementModule


class SystemMessageSubjoinModule:
    """
    System Message Subjoin Module (SMSM)
    
    Responsibilities:
    - Inject system messages into ongoing conversations
    - Manage conversation history with system interventions
    - Validate system message format and content
    - Track system message injections for audit purposes
    - Integrate with DCMM for persistent storage
    """
    MODULE_CODE = "15"  # Unique code for SMSM
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the SMSM module.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.dcmm = DatabaseControlAndManagementModule()
        
        # Error codes now generated dynamically by EMM
        
        # Statistics
        self.stats = {
            "total_injections": 0,
            "successful_injections": 0,
            "failed_injections": 0,
            "system_messages_injected": 0,
            "conversations_modified": 0,
            "last_activity": None
        }
        
        # System message templates
        self.system_templates = {
            "intervention": "SYSTEM INTERVENTION: {message}",
            "correction": "SYSTEM CORRECTION: {message}",
            "guidance": "SYSTEM GUIDANCE: {message}",
            "warning": "SYSTEM WARNING: {message}",
            "info": "SYSTEM INFO: {message}"
        }
        
        # Valid system message types
        self.valid_types = ["intervention", "correction", "guidance", "warning", "info", "custom"]
    
    def validate_system_message(self, message: str, message_type: str = "intervention") -> bool:
        """
        Validate a system message for format and content.
        
        Args:
            message: The system message content
            message_type: Type of system message
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if message is not empty
            if not message or not message.strip():
                self.logger.error("SMSM: System message cannot be empty")
                return False
            
            # Check if message type is valid
            if message_type not in self.valid_types:
                self.logger.error(f"SMSM: Invalid message type '{message_type}'")
                return False
            
            # Check message length (reasonable limit)
            if len(message) > 1000:
                self.logger.error("SMSM: System message too long (max 1000 characters)")
                return False
            
            # Check for potentially harmful content
            harmful_patterns = ["<script>", "javascript:", "eval(", "exec("]
            for pattern in harmful_patterns:
                if pattern.lower() in message.lower():
                    self.logger.error(f"SMSM: System message contains potentially harmful content: {pattern}")
                    return False
            
            return True
            
        except Exception as e:
            error_msg = f"Error validating system message: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "validate_system_message")
            return False
    
    def format_system_message(self, message: str, message_type: str = "intervention") -> str:
        """
        Format a system message according to its type.
        
        Args:
            message: The system message content
            message_type: Type of system message
            
        Returns:
            Formatted system message
        """
        try:
            if message_type == "custom":
                return f"SYSTEM: {message}"
            elif message_type in self.system_templates:
                return self.system_templates[message_type].format(message=message)
            else:
                return f"SYSTEM {message_type.upper()}: {message}"
                
        except Exception as e:
            error_msg = f"Error formatting system message: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "format_system_message")
            return f"SYSTEM: {message}"
    
    async def inject_system_message(self, request_id: str, message: str, 
                                  message_type: str = "intervention", 
                                  position: str = "end") -> Dict[str, Any]:
        """
        Inject a system message into a conversation.
        
        Args:
            request_id: Request identifier
            message: System message content
            message_type: Type of system message
            position: Where to inject the message ("start", "end", "before_last", "after_first")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate the system message
            if not self.validate_system_message(message, message_type):
                return {"success": False, "error": "Validation failed"}
            
            # Format the system message
            formatted_message = self.format_system_message(message, message_type)
            
            # Get the conversation
            conversation = await self.dcmm.get_conversation(request_id)
            if not conversation:
                error_msg = f"Conversation not found for request {request_id}"
                self.logger.error(error_msg)
                self.log_error(error_msg, "SystemMessageSubjoinModule", "inject_system_message")
                return {"success": False, "error": error_msg}
            
            # Create system message data
            system_message_data = {
                "role": "system",
                "content": formatted_message,
                "timestamp": datetime.now().isoformat(),
                "message_type": message_type,
                "injected_by": "CCU",
                "position": position
            }
            
            # Add the system message to the conversation
            success = await self.dcmm.add_message(
                request_id=request_id,
                role="system",
                content=formatted_message
            )
            
            if success:
                # Update conversation status
                await self.dcmm.update_conversation_status(request_id, "system_intervention")
                
                # Log the injection
                await self._log_system_injection(request_id, system_message_data)
                
                # Update statistics
                self.stats["total_injections"] += 1
                self.stats["successful_injections"] += 1
                self.stats["system_messages_injected"] += 1
                self.stats["conversations_modified"] += 1
                self.stats["last_activity"] = datetime.now()
                
                self.logger.info(f"SMSM: Successfully injected system message into conversation {request_id}")
                return {"success": True, "message": "System message injected successfully"}
            else:
                self.stats["total_injections"] += 1
                self.stats["failed_injections"] += 1
                return {"success": False, "error": "Failed to inject system message"}
                
        except Exception as e:
            error_msg = f"Error injecting system message for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "inject_system_message")
            self.stats["total_injections"] += 1
            self.stats["failed_injections"] += 1
            return {"success": False, "error": error_msg}
    
    async def _log_system_injection(self, request_id: str, injection_data: Dict[str, Any]) -> bool:
        """
        Log system message injection for audit purposes.
        
        Args:
            request_id: Request identifier
            injection_data: Injection data to log
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Log to error_logs database for audit trail
            error_code = self.generate_error_code("SystemMessageSubjoinModule", "log_system_injection")
            await self.dcmm.log_error(
                error_code=error_code,
                module="SMSM",
                message=f"System message injected: {injection_data['content'][:100]}...",
                recovery_attempted=False
            )
            
            # Log performance metric
            await self.dcmm.log_performance_metric(
                module="SMSM",
                metric_name="system_injection_time",
                metric_value=datetime.now().timestamp()
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Error logging system injection: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "log_system_injection")
            return False
    
    async def get_conversation_with_system_messages(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation including all system messages.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Conversation data with system messages or None if not found
        """
        try:
            conversation = await self.dcmm.get_conversation(request_id)
            if not conversation:
                return None
            
            # Filter and highlight system messages
            messages = conversation.get("messages", [])
            system_messages = []
            user_messages = []
            assistant_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_messages.append(msg)
                elif msg["role"] == "user":
                    user_messages.append(msg)
                elif msg["role"] == "assistant":
                    assistant_messages.append(msg)
            
            # Add system message summary
            conversation["system_message_count"] = len(system_messages)
            conversation["system_messages"] = system_messages
            conversation["user_message_count"] = len(user_messages)
            conversation["assistant_message_count"] = len(assistant_messages)
            
            return conversation
            
        except Exception as e:
            error_msg = f"Error getting conversation with system messages for {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "get_conversation_with_system_messages")
            return None
    
    async def remove_system_message(self, request_id: str, message_id: int) -> bool:
        """
        Remove a specific system message from a conversation.
        
        Args:
            request_id: Request identifier
            message_id: ID of the message to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the conversation
            conversation = await self.dcmm.get_conversation(request_id)
            if not conversation:
                return False
            
            # Find the system message
            messages = conversation.get("messages", [])
            system_message = None
            
            for msg in messages:
                if msg["id"] == message_id and msg["role"] == "system":
                    system_message = msg
                    break
            
            if not system_message:
                self.logger.warning(f"System message {message_id} not found in conversation {request_id}")
                return False
            
            # Remove the message from database
            success = await self.dcmm.execute(
                "conversations",
                "DELETE FROM messages WHERE id = ? AND request_id = ? AND role = 'system'",
                (message_id, request_id)
            )
            
            if success:
                self.logger.info(f"SMSM: Removed system message {message_id} from conversation {request_id}")
                return True
            else:
                return False
                
        except Exception as e:
            error_msg = f"Error removing system message {message_id} from conversation {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "remove_system_message")
            return False
    
    async def get_system_injection_history(self, request_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of system message injections for a conversation.
        
        Args:
            request_id: Request identifier
            
        Returns:
            List of system injection records
        """
        try:
            conversation = await self.dcmm.get_conversation(request_id)
            if not conversation:
                return []
            
            # Filter system messages
            system_messages = [
                msg for msg in conversation.get("messages", [])
                if msg["role"] == "system"
            ]
            
            # Add injection metadata
            for msg in system_messages:
                msg["injection_type"] = "system"
                msg["injected_by"] = "CCU"
            
            return system_messages
            
        except Exception as e:
            error_msg = f"Error getting system injection history for {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "get_system_injection_history")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the SMSM module.
        
        Returns:
            Dictionary with module status information
        """
        return {
            "module": "SMSM",
            "valid_message_types": self.valid_types,
            "system_templates": list(self.system_templates.keys()),
            "stats": self.stats.copy()
        }
    
    def reset_stats(self):
        """Reset module statistics."""
        self.stats = {
            "total_injections": 0,
            "successful_injections": 0,
            "failed_injections": 0,
            "system_messages_injected": 0,
            "conversations_modified": 0,
            "last_activity": None
        }
        self.logger.info("SMSM: Statistics reset")
    
    async def start(self):
        """Start the SMSM module."""
        self.logger.info("SMSM: Module started")
    
    async def stop(self):
        """Stop the SMSM module."""
        self.logger.info("SMSM: Module stopped")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "SMSM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("SMSM", class_name, function_name, sub_function)

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
            # Assuming api_error_handler is defined elsewhere or will be added.
            # For now, we'll just log it and return a generic error.
            self.error_manager.log_error_with_generation(
                "SMSM",
                "SMSM",
                "handle_api_error",
                f"API Error: {error_response}",
                context=context
            )
            # If api_error_handler is not defined, this will cause an error.
            # For now, we'll return a generic error.
            return {"success": False, "error": error_response}
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "SMSM",
                "SMSM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}
    
    async def inject_validation_failure_message(self, request_id: str, validation_type: str, 
                                              validation_data: Dict[str, Any], 
                                              message_type: str = "intervention") -> Dict[str, Any]:
        """
        Inject a validation failure message into a conversation.
        
        Args:
            request_id: Request identifier
            validation_type: Type of validation failure ("insufficient_data" or "invalid_data")
            validation_data: Validation analysis data from JFA
            message_type: Type of system message
            
        Returns:
            Injection result
        """
        try:
            if validation_type == "insufficient_data":
                return await self._inject_insufficient_data_message(request_id, validation_data, message_type)
            elif validation_type == "invalid_data":
                return await self._inject_invalid_data_message(request_id, validation_data, message_type)
            else:
                return {"success": False, "error": f"Unknown validation type: {validation_type}"}
                
        except Exception as e:
            error_msg = f"Error injecting validation failure message: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "inject_validation_failure_message")
            return {"success": False, "error": error_msg}
    
    async def _inject_insufficient_data_message(self, request_id: str, validation_data: Dict[str, Any], 
                                              message_type: str) -> Dict[str, Any]:
        """Inject insufficient data message."""
        try:
            missing_data = validation_data.get("missing_data", [])
            insufficient_data = validation_data.get("insufficient_data", [])
            
            # Combine missing and insufficient data
            all_missing_info = missing_data + insufficient_data
            
            if not all_missing_info:
                return {"success": False, "error": "No missing or insufficient data found"}
            
            # Format the message
            message_lines = ["The data that you send are not enough you miss this information:"]
            
            for i, info in enumerate(all_missing_info, 1):
                message_lines.append(f"{i}. {info}")
            
            formatted_message = "\n".join(message_lines)
            
            # Inject the message
            result = await self.inject_system_message(
                request_id=request_id,
                message=formatted_message,
                message_type=message_type,
                position="end"
            )
            
            # Log validation failure injection
            await self._log_validation_failure_injection(request_id, "insufficient_data", validation_data)
            
            return result
            
        except Exception as e:
            error_msg = f"Error injecting insufficient data message: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "_inject_insufficient_data_message")
            return {"success": False, "error": error_msg}
    
    async def _inject_invalid_data_message(self, request_id: str, validation_data: Dict[str, Any], 
                                         message_type: str) -> Dict[str, Any]:
        """Inject invalid data message."""
        try:
            invalid_parts = validation_data.get("invalid_parts", [])
            
            if not invalid_parts:
                return {"success": False, "error": "No invalid data parts found"}
            
            # Format the message
            message_lines = ["The data that you send are invalid you miss this parts:"]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_parts = []
            for part in invalid_parts:
                if part not in seen:
                    seen.add(part)
                    unique_parts.append(part)
            
            for i, part in enumerate(unique_parts, 1):
                message_lines.append(f"{i}. {part}")
            
            formatted_message = "\n".join(message_lines)
            
            # Inject the message
            result = await self.inject_system_message(
                request_id=request_id,
                message=formatted_message,
                message_type=message_type,
                position="end"
            )
            
            # Log validation failure injection
            await self._log_validation_failure_injection(request_id, "invalid_data", validation_data)
            
            return result
            
        except Exception as e:
            error_msg = f"Error injecting invalid data message: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "_inject_invalid_data_message")
            return {"success": False, "error": error_msg}
    
    async def _log_validation_failure_injection(self, request_id: str, validation_type: str, 
                                              validation_data: Dict[str, Any]) -> bool:
        """Log validation failure injection for audit purposes."""
        try:
            # Log to error_logs database for audit trail
            error_code = self.generate_error_code("SystemMessageSubjoinModule", "log_validation_failure_injection")
            
            validation_summary = {
                "validation_type": validation_type,
                "total_issues": len(validation_data.get("invalid_parts", [])) + 
                              len(validation_data.get("missing_data", [])) + 
                              len(validation_data.get("insufficient_data", [])),
                "request_id": request_id
            }
            
            await self.dcmm.log_error(
                error_code=error_code,
                module="SMSM",
                message=f"Validation failure message injected: {validation_type} - {validation_summary['total_issues']} issues",
                recovery_attempted=False
            )
            
            # Log performance metric
            await self.dcmm.log_performance_metric(
                module="SMSM",
                metric_name="validation_failure_injection_time",
                metric_value=datetime.now().timestamp()
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Error logging validation failure injection: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemMessageSubjoinModule", "log_validation_failure_injection")
            return False


# Global instance and alias for compatibility
smsm = SystemMessageSubjoinModule()
SMSM = SystemMessageSubjoinModule  # Class alias 
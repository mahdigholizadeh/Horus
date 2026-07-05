"""
System Model Changer Module (SMCM)

Allows the CCU to change the underlying API model or interaction module for a conversation.
If the model is changed, the entire conversation history must be resent to the new model.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import other modules for integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from DCMM.dcmm import DatabaseControlAndManagementModule
from SAAIM.saaim import SpecialAPIActivationModule


class SystemModelChangerModule:
    """
    System Model Changer Module (SMCM)
    
    Responsibilities:
    - Change the underlying API model for ongoing conversations
    - Handle conversation history migration between models
    - Validate model compatibility and availability
    - Track model changes for audit purposes
    - Integrate with SAAIM for special model interactions
    - Manage model transition states and rollback capabilities
    """
    MODULE_CODE = "16"  # Unique code for SMCM
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the SMCM module.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.dcmm = DatabaseControlAndManagementModule()
        self.saaim = SpecialAPIActivationModule()
        
        # Error codes now generated dynamically by EMM
        
        # Statistics
        self.stats = {
            "total_model_changes": 0,
            "successful_changes": 0,
            "failed_changes": 0,
            "conversations_migrated": 0,
            "rollbacks_performed": 0,
            "last_activity": None
        }
        
        # Available models and their configurations
        self.available_models = {
            "gpt-4": {
                "name": "GPT-4",
                "type": "openai",
                "max_tokens": 4096,
                "temperature": 0.7,
                "supports_functions": True,
                "supports_vision": False
            },
            "gpt-3.5-turbo": {
                "name": "GPT-3.5 Turbo",
                "type": "openai",
                "max_tokens": 4096,
                "temperature": 0.7,
                "supports_functions": True,
                "supports_vision": False
            },
            "gpt-4-vision": {
                "name": "GPT-4 Vision",
                "type": "openai",
                "max_tokens": 4096,
                "temperature": 0.7,
                "supports_functions": True,
                "supports_vision": True
            },
            "claude-3": {
                "name": "Claude 3",
                "type": "anthropic",
                "max_tokens": 4096,
                "temperature": 0.7,
                "supports_functions": True,
                "supports_vision": True
            },
            "custom": {
                "name": "Custom Model",
                "type": "special",
                "max_tokens": 1000,
                "temperature": 0.7,
                "supports_functions": False,
                "supports_vision": False
            }
        }
        
        # Model change history
        self.model_change_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def validate_model_change(self, request_id: str, new_model: str, 
                            current_model: Optional[str] = None) -> bool:
        """
        Validate a model change request.
        
        Args:
            request_id: Request identifier
            new_model: New model to change to
            current_model: Current model (optional)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if new model is available
            if new_model not in self.available_models:
                self.logger.error(f"SMCM: Model '{new_model}' is not available")
                return False
            
            # Check if conversation exists
            conversation = self.dcmm.get_conversation(request_id)
            if not conversation:
                self.logger.error(f"SMCM: Conversation not found for request {request_id}")
                return False
            
            # Check model compatibility if current model is provided
            if current_model and current_model in self.available_models:
                current_config = self.available_models[current_model]
                new_config = self.available_models[new_model]
                
                # Check if the change is supported
                if current_config["type"] != new_config["type"]:
                    self.logger.warning(f"SMCM: Changing from {current_config['type']} to {new_config['type']} model type")
            
            return True
            
        except Exception as e:
            error_msg = f"Error validating model change: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "validate_model_change")
            return False
    
    async def change_model(self, request_id: str, new_model: str, 
                          reason: str = "CCU request") -> bool:
        """
        Change the model for a conversation.
        
        Args:
            request_id: Request identifier
            new_model: New model to change to
            reason: Reason for the model change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current conversation
            conversation = await self.dcmm.get_conversation(request_id)
            if not conversation:
                error_msg = f"Conversation not found for request {request_id}"
                self.logger.error(error_msg)
                self.log_error(error_msg, "SystemModelChangerModule", "change_model")
                return False
            
            current_model = conversation.get("model", "unknown")
            
            # Validate the model change
            if not self.validate_model_change(request_id, new_model, current_model):
                return False
            
            # Store change history
            change_record = {
                "timestamp": datetime.now().isoformat(),
                "from_model": current_model,
                "to_model": new_model,
                "reason": reason,
                "status": "pending"
            }
            
            if request_id not in self.model_change_history:
                self.model_change_history[request_id] = []
            self.model_change_history[request_id].append(change_record)
            
            # Update conversation with new model
            success = self.dcmm.execute(
                "conversations",
                "UPDATE conversations SET model = ?, updated_at = CURRENT_TIMESTAMP WHERE request_id = ?",
                (new_model, request_id)
            )
            
            if success:
                # Update conversation status
                await self.dcmm.update_conversation_status(request_id, "model_changed")
                
                # Log the model change
                await self._log_model_change(request_id, change_record)
                
                # Update statistics
                self.stats["total_model_changes"] += 1
                self.stats["successful_changes"] += 1
                self.stats["conversations_migrated"] += 1
                self.stats["last_activity"] = datetime.now()
                
                # Update change record status
                change_record["status"] = "completed"
                
                self.logger.info(f"SMCM: Successfully changed model for conversation {request_id} from {current_model} to {new_model}")
                return True
            else:
                change_record["status"] = "failed"
                self.stats["total_model_changes"] += 1
                self.stats["failed_changes"] += 1
                return False
                
        except Exception as e:
            error_msg = f"Error changing model for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "change_model")
            self.stats["total_model_changes"] += 1
            self.stats["failed_changes"] += 1
            return False
    
    async def _log_model_change(self, request_id: str, change_record: Dict[str, Any]) -> bool:
        """
        Log model change for audit purposes.
        
        Args:
            request_id: Request identifier
            change_record: Model change record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Log to error_logs database for audit trail
            error_code = self.generate_error_code("SystemModelChangerModule", "log_model_change")
            await self.dcmm.log_error(
                error_code=error_code,
                module="SMCM",
                message=f"Model changed from {change_record['from_model']} to {change_record['to_model']}: {change_record['reason']}",
                recovery_attempted=False
            )
            
            # Log performance metric
            await self.dcmm.log_performance_metric(
                module="SMCM",
                metric_name="model_change_time",
                metric_value=datetime.now().timestamp()
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Error logging model change: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "log_model_change")
            return False
    
    async def get_conversation_with_model_history(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation with its model change history.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Conversation data with model history or None if not found
        """
        try:
            conversation = await self.dcmm.get_conversation(request_id)
            if not conversation:
                return None
            
            # Add model change history
            conversation["model_change_history"] = self.model_change_history.get(request_id, [])
            conversation["total_model_changes"] = len(conversation["model_change_history"])
            
            # Add current model info
            current_model = conversation.get("model", "unknown")
            if current_model in self.available_models:
                conversation["current_model_info"] = self.available_models[current_model]
            
            return conversation
            
        except Exception as e:
            error_msg = f"Error getting conversation with model history for {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "get_conversation_with_model_history")
            return None
    
    async def rollback_model_change(self, request_id: str) -> bool:
        """
        Rollback the last model change for a conversation.
        
        Args:
            request_id: Request identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get model change history
            history = self.model_change_history.get(request_id, [])
            if not history:
                self.logger.warning(f"No model change history found for request {request_id}")
                return False
            
            # Get the last change
            last_change = history[-1]
            if last_change["status"] != "completed":
                self.logger.warning(f"Last model change for {request_id} was not completed")
                return False
            
            # Rollback to previous model
            previous_model = last_change["from_model"]
            
            # Update conversation with previous model
            success = self.dcmm.execute(
                "conversations",
                "UPDATE conversations SET model = ?, updated_at = CURRENT_TIMESTAMP WHERE request_id = ?",
                (previous_model, request_id)
            )
            
            if success:
                # Update conversation status
                await self.dcmm.update_conversation_status(request_id, "model_rollback")
                
                # Add rollback record
                rollback_record = {
                    "timestamp": datetime.now().isoformat(),
                    "from_model": last_change["to_model"],
                    "to_model": previous_model,
                    "reason": "rollback",
                    "status": "completed"
                }
                history.append(rollback_record)
                
                # Update statistics
                self.stats["rollbacks_performed"] += 1
                self.stats["last_activity"] = datetime.now()
                
                self.logger.info(f"SMCM: Successfully rolled back model change for conversation {request_id}")
                return True
            else:
                return False
                
        except Exception as e:
            error_msg = f"Error rolling back model change for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "rollback_model_change")
            return False
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available models and their configurations.
        
        Returns:
            Dictionary of available models
        """
        return self.available_models.copy()
    
    def add_custom_model(self, model_id: str, model_config: Dict[str, Any]) -> bool:
        """
        Add a custom model to the available models.
        
        Args:
            model_id: Unique model identifier
            model_config: Model configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if model_id in self.available_models:
                self.logger.warning(f"Model {model_id} already exists, updating configuration")
            
            # Validate required fields
            required_fields = ["name", "type", "max_tokens", "temperature"]
            for field in required_fields:
                if field not in model_config:
                    error_msg = f"Missing required field '{field}' in model configuration"
                    self.logger.error(error_msg)
                    self.log_error(error_msg, "SystemModelChangerModule", "add_custom_model")
                    return False
            
            self.available_models[model_id] = model_config
            self.logger.info(f"SMCM: Added custom model {model_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error adding custom model {model_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "add_custom_model")
            return False
    
    def get_model_compatibility(self, model1: str, model2: str) -> Dict[str, Any]:
        """
        Check compatibility between two models.
        
        Args:
            model1: First model identifier
            model2: Second model identifier
            
        Returns:
            Compatibility information
        """
        try:
            if model1 not in self.available_models or model2 not in self.available_models:
                return {"compatible": False, "reason": "One or both models not found"}
            
            config1 = self.available_models[model1]
            config2 = self.available_models[model2]
            
            # Check type compatibility
            type_compatible = config1["type"] == config2["type"]
            
            # Check feature compatibility
            feature_compatible = (
                config1["supports_functions"] == config2["supports_functions"] and
                config1["supports_vision"] == config2["supports_vision"]
            )
            
            return {
                "compatible": type_compatible and feature_compatible,
                "type_compatible": type_compatible,
                "feature_compatible": feature_compatible,
                "model1_config": config1,
                "model2_config": config2
            }
            
        except Exception as e:
            error_msg = f"Error checking model compatibility: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "SystemModelChangerModule", "get_model_compatibility")
            return {"compatible": False, "reason": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the SMCM module.
        
        Returns:
            Dictionary with module status information
        """
        return {
            "module": "SMCM",
            "available_models": list(self.available_models.keys()),
            "total_model_changes": self.stats["total_model_changes"],
            "successful_changes": self.stats["successful_changes"],
            "failed_changes": self.stats["failed_changes"],
            "rollbacks_performed": self.stats["rollbacks_performed"],
            "stats": self.stats.copy()
        }
    
    def reset_stats(self):
        """Reset module statistics."""
        self.stats = {
            "total_model_changes": 0,
            "successful_changes": 0,
            "failed_changes": 0,
            "conversations_migrated": 0,
            "rollbacks_performed": 0,
            "last_activity": None
        }
        self.logger.info("SMCM: Statistics reset")
    
    async def start(self):
        """Start the SMCM module."""
        self.logger.info("SMCM: Module started")
    
    async def stop(self):
        """Stop the SMCM module."""
        self.logger.info("SMCM: Module stopped")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "SMCM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("SMCM", class_name, function_name, sub_function)

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
                "SMCM",
                "SMCM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "SMCM",
                "SMCM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
smcm = SystemModelChangerModule()
SMCM = SystemModelChangerModule  # Class alias 
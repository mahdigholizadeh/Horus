"""
Template Validation Module (TVM) for JFA Microservice

This module handles comprehensive template validation:
- Structure validation with complex business rules
- Data type validation and constraints
- JFA-specific validation logic
- Custom validation rule engine
- Template compliance checking
"""

import logging
import asyncio
import copy
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import re
import json


class TemplateValidationModule:
    """
    Template Validation Module
    
    Provides comprehensive template validation for JFA processing
    with support for complex business rules and custom validators.
    """
    
    def __init__(self):
        """Initialize the TVM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "TVM"
        self.is_active = False
        
        # Validation configuration
        self.validation_config = {
            "strict_mode": True,
            "enable_business_rules": True,
            "enable_custom_validators": True,
            "validation_timeout": 30,
            "max_validation_depth": 5,
            "require_all_jfa_fields": True
        }
        
        # JFA-specific validation rules
        self.jfa_validation_rules = {
            "flag": {
                "required_fields": ["vald", "calc", "plat", "mpsz", "econ", "rcon", "mode"],
                "field_types": {
                    "vald": int, "calc": int, "plat": int, "mpsz": int,
                    "econ": int, "rcon": int, "mode": int
                },
                "value_ranges": {
                    "vald": [0, 1], "calc": [0, 1], "plat": [0, 1], "mpsz": [0, 1],
                    "econ": [0, 1], "rcon": [0, 1], "mode": [0, 1]
                }
            },
            "loca": {
                "required_fields": ["Ecit", "Fcit", "lat", "lng"],
                "field_types": {
                    "Ecit": str, "Fcit": str, "lat": float, "lng": float
                },
                "validation_rules": {
                    "Ecit": {"min_length": 1, "max_length": 100},
                    "Fcit": {"min_length": 1, "max_length": 100},
                    "lat": {"min_value": -90.0, "max_value": 90.0},
                    "lng": {"min_value": -180.0, "max_value": 180.0}
                }
            },
            "cust": {
                "required_fields": ["mode", "need", "npsz"],
                "field_types": {
                    "mode": int, "need": int, "npsz": int
                },
                "value_ranges": {
                    "mode": [0, 3], "need": [0, 2], "npsz": [1, 100]
                }
            },
            "sinf": {
                "required_fields": [
                    "mfreg", "mled", "mlcd", "mtele", "mlamp", "mpump", "mcool", "mcamd",
                    "mpc", "mpri", "mwel", "mmlo", "nfreg", "nled", "nlcd", "ntele",
                    "nlamp", "npump", "ncool", "ncamd", "npc", "npri", "nwel", "nmlo"
                ],
                "field_types": {field: int for field in [
                    "mfreg", "mled", "mlcd", "mtele", "mlamp", "mpump", "mcool", "mcamd",
                    "mpc", "mpri", "mwel", "mmlo", "nfreg", "nled", "nlcd", "ntele",
                    "nlamp", "npump", "ncool", "ncamd", "npc", "npri", "nwel", "nmlo"
                ]},
                "value_ranges": {field: [0, 1000] for field in [
                    "mfreg", "mled", "mlcd", "mtele", "mlamp", "mpump", "mcool", "mcamd",
                    "mpc", "mpri", "mwel", "mmlo", "nfreg", "nled", "nlcd", "ntele",
                    "nlamp", "npump", "ncool", "ncamd", "npc", "npri", "nwel", "nmlo"
                ]}
            }
        }
        
        # Custom validation rules
        self.custom_validators = {}
        
        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "business_rule_checks": 0,
            "custom_validations": 0,
            "average_validation_time": 0.0,
            "last_activity": None
        }
        
        # Validation metrics
        self.validation_metrics = {
            "validation_success_rate": 0.0,
            "business_rule_success_rate": 0.0,
            "custom_validation_rate": 0.0,
            "validation_speed": 0.0,
            "error_distribution": {},
            "most_common_errors": []
        }
        
        # Initialize default business rules
        self._initialize_business_rules()
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    def _initialize_business_rules(self):
        """Initialize default business rules."""
        self.business_rules = {
            "payload_consistency": self._validate_payload_consistency,
            "location_consistency": self._validate_location_consistency,
            "customer_requirements_coherence": self._validate_customer_requirements_coherence,
            "flag_dependency_validation": self._validate_flag_dependencies,
            "energy_balance_validation": self._validate_energy_balance
        }
    
    async def start(self):
        """Start the TVM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the TVM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def validate_template(self, template_data: Dict[str, Any], 
                               validation_rules: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate a template according to JFA requirements.
        
        Args:
            template_data: Template data to validate
            validation_rules: Optional additional validation rules
            
        Returns:
            Validation result with detailed information
        """
        try:
            start_time = datetime.now()
            self.stats["total_validations"] += 1
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "validation_details": {},
                "business_rule_results": {},
                "custom_validation_results": {}
            }
            
            # Step 1: Basic structure validation
            structure_validation = await self._validate_basic_structure(template_data)
            validation_result["validation_details"]["structure"] = structure_validation
            
            if not structure_validation["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(structure_validation["errors"])
            
            # Step 2: JFA-specific validation
            if "jfa_data" in template_data:
                jfa_validation = await self._validate_jfa_data(template_data["jfa_data"])
                validation_result["validation_details"]["jfa_data"] = jfa_validation
                
                if not jfa_validation["valid"]:
                    validation_result["valid"] = False
                    validation_result["errors"].extend(jfa_validation["errors"])
            else:
                validation_result["valid"] = False
                validation_result["errors"].append("Missing JFA data")
            
            # Step 3: Business rule validation
            if self.validation_config["enable_business_rules"] and validation_result["valid"]:
                business_rule_validation = await self._validate_business_rules(template_data)
                validation_result["business_rule_results"] = business_rule_validation
                
                for rule_name, rule_result in business_rule_validation.items():
                    if not rule_result["valid"]:
                        validation_result["valid"] = False
                        validation_result["errors"].extend(rule_result["errors"])
                        validation_result["warnings"].extend(rule_result.get("warnings", []))
                
                self.stats["business_rule_checks"] += 1
            
            # Step 4: Custom validation rules
            if self.validation_config["enable_custom_validators"] and validation_rules:
                custom_validation = await self._apply_custom_validators(template_data, validation_rules)
                validation_result["custom_validation_results"] = custom_validation
                
                if not custom_validation["valid"]:
                    validation_result["valid"] = False
                    validation_result["errors"].extend(custom_validation["errors"])
                
                self.stats["custom_validations"] += 1
            
            # Step 5: Comprehensive validation scoring
            validation_score = self._calculate_validation_score(validation_result)
            validation_result["validation_score"] = validation_score
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            if validation_result["valid"]:
                self.stats["successful_validations"] += 1
            else:
                self.stats["failed_validations"] += 1
            
            self.stats["last_activity"] = datetime.now()
            
            # Update metrics
            await self._update_validation_metrics(validation_result, processing_time)
            
            # Add validated data if successful
            if validation_result["valid"]:
                validation_result["validated_data"] = copy.deepcopy(template_data)
                validation_result["complex_validation"] = True
            
            validation_result["processing_time"] = processing_time
            validation_result["timestamp"] = datetime.now().isoformat()
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating template: {e}")
            self.stats["failed_validations"] += 1
            return {
                "valid": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _validate_basic_structure(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate basic template structure."""
        try:
            errors = []
            
            # Check required top-level fields
            required_fields = ["id", "object", "created", "model"]
            for field in required_fields:
                if field not in template_data:
                    errors.append(f"Missing required field: {field}")
                elif not template_data[field]:
                    errors.append(f"Empty required field: {field}")
            
            # Validate data types
            if "id" in template_data and not isinstance(template_data["id"], str):
                errors.append("Field 'id' must be a string")
            
            if "created" in template_data and not isinstance(template_data["created"], (int, float)):
                errors.append("Field 'created' must be a number")
            
            if "model" in template_data and not isinstance(template_data["model"], str):
                errors.append("Field 'model' must be a string")
            
            # Check message structure
            if "message" in template_data:
                message = template_data["message"]
                if not isinstance(message, dict):
                    errors.append("Field 'message' must be a dictionary")
                else:
                    if "role" not in message:
                        errors.append("Missing 'role' in message")
                    if "content" not in message:
                        errors.append("Missing 'content' in message")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "structure_score": max(0, 100 - len(errors) * 15)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Structure validation error: {str(e)}"],
                "structure_score": 0
            }
    
    async def _validate_jfa_data(self, jfa_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JFA-specific data."""
        try:
            errors = []
            validation_details = {}
            
            # Validate each JFA section
            for section_name, section_rules in self.jfa_validation_rules.items():
                if section_name not in jfa_data:
                    errors.append(f"Missing JFA section: {section_name}")
                    continue
                
                section_data = jfa_data[section_name]
                section_validation = await self._validate_jfa_section(section_data, section_rules, section_name)
                validation_details[section_name] = section_validation
                
                if not section_validation["valid"]:
                    errors.extend(section_validation["errors"])
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "section_details": validation_details,
                "jfa_score": max(0, 100 - len(errors) * 10)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"JFA data validation error: {str(e)}"],
                "jfa_score": 0
            }
    
    async def _validate_jfa_section(self, section_data: Dict[str, Any], 
                                   rules: Dict[str, Any], section_name: str) -> Dict[str, Any]:
        """Validate a specific JFA section."""
        try:
            errors = []
            
            # Check required fields
            for field in rules["required_fields"]:
                if field not in section_data:
                    errors.append(f"Missing required field in {section_name}: {field}")
            
            # Check field types and values
            for field, field_type in rules["field_types"].items():
                if field in section_data:
                    value = section_data[field]
                    
                    # Type validation
                    if not isinstance(value, field_type):
                        try:
                            # Try to convert
                            section_data[field] = field_type(value)
                        except (ValueError, TypeError):
                            errors.append(f"Invalid type for {section_name}.{field}: expected {field_type.__name__}")
                    
                    # Range validation
                    if "value_ranges" in rules and field in rules["value_ranges"]:
                        min_val, max_val = rules["value_ranges"][field]
                        if not (min_val <= section_data[field] <= max_val):
                            errors.append(f"Value out of range for {section_name}.{field}: {section_data[field]} (expected {min_val}-{max_val})")
                    
                    # Additional validation rules
                    if "validation_rules" in rules and field in rules["validation_rules"]:
                        field_rules = rules["validation_rules"][field]
                        
                        if field_type == str:
                            if "min_length" in field_rules and len(str(value)) < field_rules["min_length"]:
                                errors.append(f"String too short for {section_name}.{field}: {len(str(value))} < {field_rules['min_length']}")
                            if "max_length" in field_rules and len(str(value)) > field_rules["max_length"]:
                                errors.append(f"String too long for {section_name}.{field}: {len(str(value))} > {field_rules['max_length']}")
                        
                        elif field_type in [int, float]:
                            if "min_value" in field_rules and value < field_rules["min_value"]:
                                errors.append(f"Value too small for {section_name}.{field}: {value} < {field_rules['min_value']}")
                            if "max_value" in field_rules and value > field_rules["max_value"]:
                                errors.append(f"Value too large for {section_name}.{field}: {value} > {field_rules['max_value']}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "section_score": max(0, 100 - len(errors) * 20)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Section validation error for {section_name}: {str(e)}"],
                "section_score": 0
            }
    
    async def _validate_business_rules(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business rules."""
        try:
            business_rule_results = {}
            
            for rule_name, rule_function in self.business_rules.items():
                try:
                    rule_result = await rule_function(template_data)
                    business_rule_results[rule_name] = rule_result
                except Exception as e:
                    business_rule_results[rule_name] = {
                        "valid": False,
                        "errors": [f"Business rule error: {str(e)}"],
                        "warnings": []
                    }
            
            return business_rule_results
            
        except Exception as e:
            return {
                "error": f"Business rule validation error: {str(e)}"
            }
    
    async def _validate_payload_consistency(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate request payload consistency for proxy routing."""
        try:
            errors = []
            warnings = []

            payload = template_data.get("payload") or template_data.get("jfa_data", {}).get("payload")
            route = template_data.get("route") or template_data.get("jfa_data", {}).get("route", "forward")

            if route not in ("forward", "parallel", "sequential"):
                errors.append(f"Unsupported route: {route}")

            if payload is None and template_data.get("jfa_data", {}).get("flag", {}).get("calc", 0) == 1:
                warnings.append("Routing enabled but payload section is empty")

            return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

        except Exception as e:
            return {"valid": False, "errors": [f"Payload consistency error: {str(e)}"], "warnings": []}

    async def _validate_solar_calculation_consistency(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecated alias — use payload consistency validation."""
        return await self._validate_payload_consistency(template_data)
    
    async def _validate_location_consistency(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate location consistency."""
        try:
            errors = []
            warnings = []
            
            if "jfa_data" not in template_data or "loca" not in template_data["jfa_data"]:
                return {"valid": False, "errors": ["Missing location data"], "warnings": []}
            
            loca_data = template_data["jfa_data"]["loca"]
            
            # Check coordinate validity
            lat = loca_data.get("lat", 0)
            lng = loca_data.get("lng", 0)
            
            if lat == 0 and lng == 0:
                errors.append("Invalid coordinates: both latitude and longitude are zero")

            if not (-90.0 <= lat <= 90.0):
                errors.append(f"Latitude {lat} out of valid range (-90 to 90)")

            if not (-180.0 <= lng <= 180.0):
                errors.append(f"Longitude {lng} out of valid range (-180 to 180)")
            
            if not (44.0 <= lng <= 64.0):
                warnings.append(f"Longitude {lng} may be outside Iran's bounds")
            
            # Check city name consistency
            ecit = loca_data.get("Ecit", "").lower()
            fcit = loca_data.get("Fcit", "")
            
            if not ecit:
                errors.append("Missing English city name")
            
            if not fcit:
                errors.append("Missing Farsi city name")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Location consistency error: {str(e)}"],
                "warnings": []
            }
    
    async def _validate_customer_requirements_coherence(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate customer requirements coherence."""
        try:
            errors = []
            warnings = []
            
            if "jfa_data" not in template_data or "cust" not in template_data["jfa_data"]:
                return {"valid": False, "errors": ["Missing customer data"], "warnings": []}
            
            cust_data = template_data["jfa_data"]["cust"]
            
            # Check mode and need consistency
            mode = cust_data.get("mode", 0)
            need = cust_data.get("need", 0)
            npsz = cust_data.get("npsz", 0)
            
            if mode == 0 and need > 0:
                warnings.append("Customer mode is 0 but need is specified")
            
            if need == 0 and npsz > 0:
                warnings.append("Customer need is 0 but panel size is specified")
            
            if npsz <= 0:
                errors.append("Invalid panel size: must be greater than 0")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Customer requirements coherence error: {str(e)}"],
                "warnings": []
            }
    
    async def _validate_flag_dependencies(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate flag dependencies."""
        try:
            errors = []
            warnings = []
            
            if "jfa_data" not in template_data or "flag" not in template_data["jfa_data"]:
                return {"valid": False, "errors": ["Missing flag data"], "warnings": []}
            
            flag_data = template_data["jfa_data"]["flag"]
            
            # Check flag dependencies
            vald = flag_data.get("vald", 0)
            calc = flag_data.get("calc", 0)
            
            if vald == 0 and calc == 1:
                errors.append("Cannot enable calculation without validation")
            
            if calc == 1:
                plat = flag_data.get("plat", 0)
                if plat == 0:
                    warnings.append("Calculation enabled but platform validation disabled")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Flag dependencies error: {str(e)}"],
                "warnings": []
            }
    
    async def _validate_energy_balance(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate energy balance."""
        try:
            errors = []
            warnings = []
            
            if "jfa_data" not in template_data or "sinf" not in template_data["jfa_data"]:
                return {"valid": False, "errors": ["Missing solar information"], "warnings": []}
            
            sinf_data = template_data["jfa_data"]["sinf"]
            
            # Calculate morning and night energy consumption
            morning_items = ["mfreg", "mled", "mlcd", "mtele", "mlamp", "mpump", "mcool", "mcamd", "mpc", "mpri", "mwel", "mmlo"]
            night_items = ["nfreg", "nled", "nlcd", "ntele", "nlamp", "npump", "ncool", "ncamd", "npc", "npri", "nwel", "nmlo"]
            
            morning_total = sum(sinf_data.get(item, 0) for item in morning_items)
            night_total = sum(sinf_data.get(item, 0) for item in night_items)
            
            # Check for unrealistic energy consumption
            if morning_total > 10000:
                warnings.append(f"Very high morning energy consumption: {morning_total}")
            
            if night_total > 10000:
                warnings.append(f"Very high night energy consumption: {night_total}")
            
            # Check for zero consumption
            if morning_total == 0 and night_total == 0:
                errors.append("Zero energy consumption specified")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Energy balance error: {str(e)}"],
                "warnings": []
            }
    
    async def _apply_custom_validators(self, template_data: Dict[str, Any], 
                                     validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom validation rules."""
        try:
            errors = []
            custom_results = {}
            
            for rule_name, rule_config in validation_rules.items():
                if rule_name in self.custom_validators:
                    validator = self.custom_validators[rule_name]
                    result = await validator(template_data, rule_config)
                    custom_results[rule_name] = result
                    
                    if not result.get("valid", True):
                        errors.extend(result.get("errors", []))
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "custom_results": custom_results
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Custom validation error: {str(e)}"],
                "custom_results": {}
            }
    
    def _calculate_validation_score(self, validation_result: Dict[str, Any]) -> float:
        """Calculate overall validation score."""
        try:
            base_score = 100.0
            
            # Deduct points for errors
            error_count = len(validation_result.get("errors", []))
            base_score -= error_count * 20
            
            # Deduct points for warnings
            warning_count = len(validation_result.get("warnings", []))
            base_score -= warning_count * 5
            
            # Bonus for passing business rules
            business_rules_passed = 0
            total_business_rules = len(self.business_rules)
            
            for rule_result in validation_result.get("business_rule_results", {}).values():
                if rule_result.get("valid", False):
                    business_rules_passed += 1
            
            if total_business_rules > 0:
                business_rule_bonus = (business_rules_passed / total_business_rules) * 10
                base_score += business_rule_bonus
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating validation score: {e}")
            return 0.0
    
    async def _update_validation_metrics(self, validation_result: Dict[str, Any], processing_time: float):
        """Update validation metrics."""
        try:
            # Update success rate
            total_validations = self.stats["total_validations"]
            if total_validations > 0:
                self.validation_metrics["validation_success_rate"] = (
                    self.stats["successful_validations"] / total_validations
                )
            
            # Update processing speed
            current_speed = self.validation_metrics["validation_speed"]
            new_speed = 1.0 / processing_time if processing_time > 0 else 0
            self.validation_metrics["validation_speed"] = (
                (current_speed * (total_validations - 1) + new_speed) / total_validations
            )
            
            # Update average validation time
            current_avg = self.stats["average_validation_time"]
            self.stats["average_validation_time"] = (
                (current_avg * (total_validations - 1) + processing_time) / total_validations
            )
            
            # Update business rule success rate
            business_rule_results = validation_result.get("business_rule_results", {})
            if self.stats["business_rule_checks"] > 0 and business_rule_results:
                business_rule_successes = sum(
                    1 for result in business_rule_results.values()
                    if result.get("valid", False)
                )
                self.validation_metrics["business_rule_success_rate"] = (
                    business_rule_successes / len(business_rule_results)
                )
            
            # Update error distribution
            for error in validation_result.get("errors", []):
                error_type = error.split(":")[0] if ":" in error else "general"
                self.validation_metrics["error_distribution"][error_type] = (
                    self.validation_metrics["error_distribution"].get(error_type, 0) + 1
                )
            
            # Update most common errors
            error_counts = self.validation_metrics["error_distribution"]
            self.validation_metrics["most_common_errors"] = sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
            
        except Exception as e:
            self.logger.error(f"Error updating validation metrics: {e}")
    
    async def add_custom_validator(self, name: str, validator: Callable):
        """Add a custom validator."""
        try:
            self.custom_validators[name] = validator
            self.logger.info(f"Added custom validator: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding custom validator {name}: {e}")
            return False
    
    async def remove_custom_validator(self, name: str):
        """Remove a custom validator."""
        try:
            if name in self.custom_validators:
                del self.custom_validators[name]
                self.logger.info(f"Removed custom validator: {name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing custom validator {name}: {e}")
            return False
    
    async def get_validation_rules(self) -> Dict[str, Any]:
        """Get current validation rules."""
        return {
            "jfa_validation_rules": self.jfa_validation_rules,
            "business_rules": list(self.business_rules.keys()),
            "custom_validators": list(self.custom_validators.keys()),
            "validation_config": self.validation_config
        }
    
    async def update_validation_rules(self, rules: Dict[str, Any]) -> bool:
        """Update validation rules."""
        try:
            if "jfa_validation_rules" in rules:
                self.jfa_validation_rules.update(rules["jfa_validation_rules"])
            
            if "validation_config" in rules:
                self.validation_config.update(rules["validation_config"])
            
            self.logger.info("Validation rules updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating validation rules: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the TVM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "validation_metrics": self.validation_metrics,
            "configuration": self.validation_config,
            "business_rules": list(self.business_rules.keys()),
            "custom_validators": list(self.custom_validators.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test validation with sample data
            test_template = {
                "id": "test-001",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "gpt-4",
                "message": {
                    "role": "assistant",
                    "content": "test content"
                },
                "jfa_data": {
                    "flag": {"vald": 1, "calc": 1, "plat": 1, "mpsz": 1, "econ": 1, "rcon": 0, "mode": 1},
                    "loca": {"Ecit": "tehran", "Fcit": "تهران", "lat": 35.6892, "lng": 51.3889},
                    "cust": {"mode": 1, "need": 1, "npsz": 5},
                    "sinf": {
                        "mfreg": 1, "mled": 1, "mlcd": 1, "mtele": 1, "mlamp": 1, "mpump": 1,
                        "mcool": 1, "mcamd": 1, "mpc": 1, "mpri": 1, "mwel": 1, "mmlo": 1,
                        "nfreg": 0, "nled": 0, "nlcd": 0, "ntele": 0, "nlamp": 0, "npump": 0,
                        "ncool": 0, "ncamd": 0, "npc": 0, "npri": 0, "nwel": 0, "nmlo": 0
                    }
                }
            }
            
            start_time = datetime.now()
            result = await self.validate_template(test_template)
            test_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "healthy": self.is_active and result["valid"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_performance": test_time,
                "validation_capabilities": {
                    "structure_validation": True,
                    "jfa_validation": True,
                    "business_rules": True,
                    "custom_validators": len(self.custom_validators) > 0
                },
                "statistics": self.stats
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 
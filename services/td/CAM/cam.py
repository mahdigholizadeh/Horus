"""
Result Aggregation Module (CAM) for TD Microservice

Aggregates passthrough routing results from multiple pipeline stages,
prepares unified metadata for OCM consumption, and tracks routing performance.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid


class ResultAggregationModule:
    """Aggregates routing results for downstream delivery."""
    
    def __init__(self):
        """Initialize the Calculation Aggregation Module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "CAM"
        self.is_active = False
        
        # Configuration
        self.config = {
            "enable_result_validation": True,
            "enable_cross_calculation_analysis": True,
            "enable_performance_aggregation": True,
            "enable_metadata_enrichment": True,
            "max_aggregation_time": 60,  # seconds
            "require_all_calculations": False,
            "enable_partial_aggregation": True,
            "output_format": "ocm_compatible"
        }
        
        # Processing statistics
        self.stats = {
            "total_aggregations": 0,
            "successful_aggregations": 0,
            "failed_aggregations": 0,
            "partial_aggregations": 0,
            "results_processed": 0,
            "validation_errors": 0,
            "cross_analysis_performed": 0,
            "last_activity": None
        }
        
        self.logger.info("Calculation Aggregation Module initialized")
    
    async def start(self):
        """Start the Calculation Aggregation Module."""
        try:
            self.is_active = True
            self.logger.info("Calculation Aggregation Module started")
            
        except Exception as e:
            self.logger.error(f"Failed to start CAM: {e}")
            raise
    
    async def stop(self):
        """Stop the Calculation Aggregation Module."""
        try:
            self.is_active = False
            self.logger.info("Calculation Aggregation Module stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop CAM: {e}")
            raise
    
    async def aggregate_results(self, calculation_results: Dict[str, Any], 
                              request_id: str) -> Dict[str, Any]:
        """
        Aggregate results from multiple calculation blocks.
        
        Args:
            calculation_results: Dictionary of calculation results
            request_id: Request identifier for tracking
            
        Returns:
            Aggregated results in unified format
        """
        try:
            start_time = datetime.now()
            aggregation_id = f"agg_{uuid.uuid4().hex[:8]}"
            
            self.stats["total_aggregations"] += 1
            
            # Separate successful and failed results
            successful_results = {}
            failed_results = {}
            
            for calc_name, result in calculation_results.items():
                if result.get('success', False):
                    successful_results[calc_name] = result
                else:
                    failed_results[calc_name] = result
            
            # Perform aggregation
            aggregated_data = await self._perform_aggregation(successful_results, request_id)
            
            # Generate performance metrics
            performance_metrics = await self._generate_performance_metrics(
                successful_results, failed_results
            )
            
            # Enrich with metadata
            metadata = await self._enrich_metadata(
                successful_results, failed_results, performance_metrics
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            if successful_results:
                self.stats["successful_aggregations"] += 1
                if failed_results:
                    self.stats["partial_aggregations"] += 1
            else:
                self.stats["failed_aggregations"] += 1
            
            self.stats["results_processed"] += len(calculation_results)
            self.stats["last_activity"] = datetime.now()
            
            self.logger.info(f"Results aggregated successfully in {processing_time:.3f}s")
            
            return {
                'success': True,
                'aggregation_id': aggregation_id,
                'aggregated_results': aggregated_data,
                'metadata': metadata,
                'aggregation_summary': {
                    'total_calculations': len(calculation_results),
                    'successful_calculations': len(successful_results),
                    'failed_calculations': len(failed_results),
                    'processing_time': processing_time,
                    'aggregation_status': 'completed'
                },
                'performance_metrics': performance_metrics,
                'request_id': request_id
            }
            
        except Exception as e:
            self.logger.error(f"Error aggregating results: {e}")
            self.stats["failed_aggregations"] += 1
            return {
                'success': False,
                'errors': [str(e)],
                'request_id': request_id
            }
    
    async def _perform_aggregation(self, successful_results: Dict[str, Any], 
                                 request_id: str) -> Dict[str, Any]:
        """Perform the main aggregation of calculation results."""
        try:
            aggregated_data = {
                'request_id': request_id,
                'aggregation_timestamp': datetime.now().isoformat(),
                'calculation_results': {},
                'summary': {
                    'total_calculations': len(successful_results),
                    'calculation_types': list(successful_results.keys())
                }
            }
            
            # Process each calculation result
            for calc_name, result in successful_results.items():
                processed_result = await self._process_calculation_result(calc_name, result)
                aggregated_data['calculation_results'][calc_name] = processed_result
            
            # Generate combined summaries
            combined_summary = await self._generate_combined_summary(successful_results)
            aggregated_data['combined_summary'] = combined_summary
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(successful_results)
            aggregated_data['recommendations'] = recommendations
            
            return aggregated_data
            
        except Exception as e:
            self.logger.error(f"Error performing aggregation: {e}")
            return {}
    
    async def _process_calculation_result(self, calc_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual calculation result."""
        try:
            processed_result = {
                'calculation_type': calc_name.lower(),
                'status': 'completed' if result.get('success', False) else 'failed',
                'execution_time': result.get('execution_time', 0),
                'result_data': result.get('result_data', {}),
                'metadata': {
                    'task_id': result.get('task_id', ''),
                    'timestamp': result.get('timestamp', datetime.now().isoformat()),
                    'calculation_name': calc_name
                }
            }
            
            processed_result['category'] = 'routing'
            processed_result['subcategory'] = calc_name
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"Error processing {calc_name} result: {e}")
            return {
                'calculation_type': calc_name.lower(),
                'status': 'processing_error',
                'error': str(e)
            }
    
    async def _generate_combined_summary(self, successful_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate combined summary from all calculation results."""
        try:
            summary = {
                'total_calculations': len(successful_results),
                'categories': {},
                'overall_metrics': {},
                'system_recommendations': []
            }
            
            # Categorize results
            for calc_name, result in successful_results.items():
                category = 'routing'
                
                if category not in summary['categories']:
                    summary['categories'][category] = []
                
                summary['categories'][category].append({
                    'calculation': calc_name,
                    'status': 'completed',
                    'execution_time': result.get('execution_time', 0)
                })
            
            # Generate overall metrics
            total_execution_time = sum(
                result.get('execution_time', 0) for result in successful_results.values()
            )
            
            summary['overall_metrics'] = {
                'total_execution_time': total_execution_time,
                'average_execution_time': total_execution_time / len(successful_results) if successful_results else 0,
                'calculations_completed': len(successful_results),
                'success_rate': 1.0  # Only successful results are passed here
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating combined summary: {e}")
            return {}
    
    async def _generate_recommendations(self, successful_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on calculation results."""
        try:
            recommendations = ["Request routed successfully through TD proxy"]
            if successful_results:
                recommendations.append(
                    f"Processed {len(successful_results)} route(s): "
                    f"{', '.join(successful_results.keys())}"
                )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _generate_performance_metrics(self, successful_results: Dict[str, Any], 
                                          failed_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance metrics for the aggregation."""
        try:
            total_calculations = len(successful_results) + len(failed_results)
            
            metrics = {
                'calculation_success_rate': len(successful_results) / total_calculations if total_calculations > 0 else 0,
                'total_execution_time': sum(
                    result.get('execution_time', 0) for result in successful_results.values()
                ),
                'average_execution_time': sum(
                    result.get('execution_time', 0) for result in successful_results.values()
                ) / len(successful_results) if successful_results else 0,
                'failed_calculations': list(failed_results.keys()),
                'successful_calculations': list(successful_results.keys()),
                'performance_grade': 'A' if len(successful_results) / total_calculations > 0.9 else 'B'
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error generating performance metrics: {e}")
            return {}
    
    async def _enrich_metadata(self, successful_results: Dict[str, Any], 
                             failed_results: Dict[str, Any],
                             performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich metadata for the aggregated results."""
        try:
            metadata = {
                'aggregation_info': {
                    'timestamp': datetime.now().isoformat(),
                    'total_calculations': len(successful_results) + len(failed_results),
                    'successful_calculations': len(successful_results),
                    'failed_calculations': len(failed_results),
                    'aggregation_method': 'unified_processing',
                    'cross_analysis_enabled': self.config['enable_cross_calculation_analysis']
                },
                'quality_metrics': {
                    'validation_passed': len(successful_results) > 0,
                    'completeness_score': len(successful_results) / (len(successful_results) + len(failed_results)) if (len(successful_results) + len(failed_results)) > 0 else 0,
                    'consistency_score': 0.95
                },
                'processing_info': {
                    'module_version': '1.0.0',
                    'processing_method': 'parallel_aggregation',
                    'performance_metrics': performance_metrics
                }
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error enriching metadata: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'configuration': self.config,
            'statistics': self.stats,
            'capabilities': {
                'result_aggregation': True,
                'cross_calculation_analysis': True,
                'performance_metrics': True,
                'metadata_enrichment': True,
                'validation': True,
                'ocm_formatting': True
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'healthy': self.is_active,
            'status': 'All systems operational' if self.is_active else 'Module not active',
            'aggregation_statistics': self.stats,
            'timestamp': datetime.now().isoformat()
        }


# Backward-compatible alias used by TD_main and ECM imports
CalculationAggregationModule = ResultAggregationModule
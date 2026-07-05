"""
Request Tracking Module (RTM)

The core of the CCU orchestration logic. This module manages the end-to-end workflow
for each request, including state tracking, routing to appropriate microservices,
and handling responses before passing to the next stage.

Key Responsibilities:
- Request lifecycle management with unique request_id tracking
- Workflow orchestration across all microservices
- State persistence and recovery
- Request routing and handoff between services
- Performance monitoring and optimization
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
import uuid


class WorkflowStage(Enum):
    """Enumeration for workflow stages."""
    RECEIVED = "received"
    RLA_VALIDATION = "rla_validation"
    TPP_PROCESSING = "tpp_processing"
    RCM_PROCESSING = "rcm_processing"
    JFA_ANALYSIS = "jfa_analysis"
    TD_CALCULATION = "td_calculation"
    OCM_OUTPUT = "ocm_output"
    COMPLETED = "completed"
    FAILED = "failed"


class RequestStatus(Enum):
    """Enumeration for request status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class WorkflowContext:
    """Context information for workflow tracking."""
    request_id: str
    status: RequestStatus
    current_stage: WorkflowStage
    created_at: datetime
    updated_at: datetime
    workflow_type: str
    processing_history: List[Dict[str, Any]]
    error_count: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RequestTrackingModule:
    """
    Request Tracking Module (RTM)
    
    Core module for managing request workflows and orchestrating
    the entire service pipeline.
    """
    
    def __init__(self):
        """Initialize the RTM module."""
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path("rtm_database.db")
        self.init_database()
        
        # Active workflows
        self.active_workflows: Dict[str, WorkflowContext] = {}
        
        # Workflow definitions
        self.standard_workflow = [
            WorkflowStage.RECEIVED,
            WorkflowStage.RLA_VALIDATION,
            WorkflowStage.TPP_PROCESSING,
            WorkflowStage.RCM_PROCESSING,
            WorkflowStage.JFA_ANALYSIS,
            WorkflowStage.TD_CALCULATION,
            WorkflowStage.OCM_OUTPUT,
            WorkflowStage.COMPLETED
        ]
        
        self.ai_only_workflow = [
            WorkflowStage.RECEIVED,
            WorkflowStage.RLA_VALIDATION,
            WorkflowStage.TPP_PROCESSING,
            WorkflowStage.RCM_PROCESSING,
            WorkflowStage.OCM_OUTPUT,
            WorkflowStage.COMPLETED
        ]
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0,
            "workflow_performance": {}
        }
        
        self.logger.info("RTM module initialized successfully")
    
    def init_database(self):
        """Initialize the RTM database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create workflows table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    request_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_count INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    processing_history TEXT
                )
            ''')
            
            # Create performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES workflows (request_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("RTM database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize RTM database: {e}")
            raise
    
    async def start(self):
        """Start the RTM module."""
        try:
            # Load existing workflows from database
            await self.load_existing_workflows()
            
            # Start background tasks
            asyncio.create_task(self.cleanup_old_workflows())
            asyncio.create_task(self.monitor_workflow_performance())
            
            self.logger.info("RTM module started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start RTM module: {e}")
            raise
    
    async def stop(self):
        """Stop the RTM module."""
        try:
            # Save all active workflows to database
            await self.save_all_workflows()
            
            self.logger.info("RTM module stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop RTM module: {e}")
            raise
    
    async def orchestrate_request(self, request_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Orchestrate a request through the entire workflow pipeline.
        
        Args:
            request_data: The request data to process
            context: Request context from CCU
            
        Returns:
            Processing result
        """
        try:
            request_id = request_data.get('request_id')
            if not request_id:
                raise ValueError("Request ID is required")
            
            self.logger.info(f"Starting workflow orchestration for request {request_id}")
            
            # Check if workflow already exists
            if request_id in self.active_workflows:
                workflow_context = self.active_workflows[request_id]
                self.logger.info(f"Resuming existing workflow for request {request_id}")
            else:
                # Create new workflow
                workflow_context = await self.create_workflow(request_data)
                self.active_workflows[request_id] = workflow_context
            
            # Execute the workflow
            result = await self.execute_workflow(workflow_context, request_data)
            
            # Update statistics
            self.stats['total_requests'] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error orchestrating request {request_id}: {e}")
            # Update failure statistics
            self.stats['failed_requests'] += 1
            raise
    
    async def create_workflow(self, request_data: Dict[str, Any]) -> WorkflowContext:
        """Create a new workflow context."""
        try:
            request_id = request_data.get('request_id')
            
            # Determine workflow type
            workflow_type = self.determine_workflow_type(request_data)
            
            # Create workflow context
            workflow_context = WorkflowContext(
                request_id=request_id,
                status=RequestStatus.PENDING,
                current_stage=WorkflowStage.RECEIVED,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                workflow_type=workflow_type,
                processing_history=[],
                metadata=request_data.get('metadata', {})
            )
            
            # Save to database
            await self.save_workflow_to_db(workflow_context)
            
            self.logger.info(f"Created new workflow for request {request_id} with type {workflow_type}")
            
            return workflow_context
            
        except Exception as e:
            self.logger.error(f"Error creating workflow: {e}")
            raise
    
    def determine_workflow_type(self, request_data: Dict[str, Any]) -> str:
        """Determine the appropriate workflow type based on request data."""
        if request_data.get('requires_calculation', False):
            return "full_workflow"
        
        if request_data.get('template_type'):
            return "template_workflow"
        
        return "ai_workflow"
    
    async def execute_workflow(self, workflow_context: WorkflowContext, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow stages."""
        try:
            workflow_stages = self.get_workflow_stages(workflow_context.workflow_type)
            
            for stage in workflow_stages:
                if workflow_context.current_stage == stage:
                    continue  # Skip already completed stages
                
                # Execute stage
                stage_result = await self.execute_stage(stage, workflow_context, request_data)
                
                # Update workflow context
                workflow_context.current_stage = stage
                workflow_context.updated_at = datetime.now()
                workflow_context.processing_history.append({
                    'stage': stage.value,
                    'timestamp': datetime.now().isoformat(),
                    'result': stage_result,
                    'success': stage_result.get('success', False)
                })
                
                # Save progress
                await self.save_workflow_to_db(workflow_context)
                
                # Check for errors
                if not stage_result.get('success', False):
                    workflow_context.status = RequestStatus.FAILED
                    workflow_context.error_count += 1
                    
                    # Attempt retry if appropriate
                    if workflow_context.retry_count < 3:
                        workflow_context.retry_count += 1
                        workflow_context.status = RequestStatus.RETRYING
                        self.logger.warning(f"Stage {stage.value} failed for request {workflow_context.request_id}, retrying...")
                        # Implement retry logic
                        continue
                    else:
                        self.logger.error(f"Stage {stage.value} failed for request {workflow_context.request_id} after maximum retries")
                        break
                
                # Update request data with stage result
                request_data.update(stage_result.get('data', {}))
            
            # Mark workflow as completed
            if workflow_context.current_stage == WorkflowStage.COMPLETED:
                workflow_context.status = RequestStatus.COMPLETED
                self.stats['completed_requests'] += 1
                
                # Remove from active workflows
                if workflow_context.request_id in self.active_workflows:
                    del self.active_workflows[workflow_context.request_id]
            
            return {
                'success': workflow_context.status == RequestStatus.COMPLETED,
                'request_id': workflow_context.request_id,
                'final_stage': workflow_context.current_stage.value,
                'status': workflow_context.status.value,
                'data': request_data
            }
            
        except Exception as e:
            self.logger.error(f"Error executing workflow: {e}")
            workflow_context.status = RequestStatus.FAILED
            workflow_context.error_count += 1
            await self.save_workflow_to_db(workflow_context)
            raise
    
    def get_workflow_stages(self, workflow_type: str) -> List[WorkflowStage]:
        """Get the appropriate workflow stages based on type."""
        if workflow_type == "full_workflow":
            return self.standard_workflow
        elif workflow_type == "ai_workflow":
            return self.ai_only_workflow
        elif workflow_type == "template_workflow":
            return self.standard_workflow
        else:
            return self.ai_only_workflow
    
    async def execute_stage(self, stage: WorkflowStage, workflow_context: WorkflowContext, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific workflow stage."""
        try:
            stage_start_time = datetime.now()
            
            self.logger.info(f"Executing stage {stage.value} for request {workflow_context.request_id}")
            
            # Record performance metrics
            await self.record_stage_start(workflow_context.request_id, stage.value, stage_start_time)
            
            # Execute stage based on type
            if stage == WorkflowStage.RECEIVED:
                result = await self.stage_received(request_data)
            elif stage == WorkflowStage.RLA_VALIDATION:
                result = await self.stage_rla_validation(request_data)
            elif stage == WorkflowStage.TPP_PROCESSING:
                result = await self.stage_tpp_processing(request_data)
            elif stage == WorkflowStage.RCM_PROCESSING:
                result = await self.stage_rcm_processing(request_data)
            elif stage == WorkflowStage.JFA_ANALYSIS:
                result = await self.stage_jfa_analysis(request_data)
            elif stage == WorkflowStage.TD_CALCULATION:
                result = await self.stage_td_calculation(request_data)
            elif stage == WorkflowStage.OCM_OUTPUT:
                result = await self.stage_ocm_output(request_data)
            elif stage == WorkflowStage.COMPLETED:
                result = await self.stage_completed(request_data)
            else:
                result = {'success': False, 'error': f'Unknown stage: {stage.value}'}
            
            # Record completion
            stage_end_time = datetime.now()
            duration = (stage_end_time - stage_start_time).total_seconds()
            
            await self.record_stage_completion(
                workflow_context.request_id,
                stage.value,
                stage_end_time,
                duration,
                result.get('success', False),
                result.get('error', None)
            )
            
            self.logger.info(f"Completed stage {stage.value} for request {workflow_context.request_id} in {duration:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing stage {stage.value}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def stage_received(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the received stage."""
        return {'success': True, 'message': 'Request received and validated'}
    
    async def stage_rla_validation(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle RLA validation stage."""
        # This would interact with the RLA service via RLAIM module
        # For now, return success
        return {'success': True, 'message': 'RLA validation completed'}
    
    async def stage_tpp_processing(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle TPP processing stage."""
        # This would interact with the TPP service via TPPIM module
        # For now, return success
        return {'success': True, 'message': 'TPP processing completed'}
    
    async def stage_rcm_processing(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle RCM processing stage."""
        # This would interact with the RCM service via RCMIM module
        # For now, return success
        return {'success': True, 'message': 'RCM processing completed'}
    
    async def stage_jfa_analysis(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JFA analysis stage."""
        # This would interact with the JFA service via JFAIM module
        # For now, return success
        return {'success': True, 'message': 'JFA analysis completed'}
    
    async def stage_td_calculation(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle TD calculation stage."""
        # This would interact with the TD service via TDIM module
        # For now, return success
        return {'success': True, 'message': 'TD calculation completed'}
    
    async def stage_ocm_output(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle OCM output stage."""
        # This would interact with the OCM service via OCMIM module
        # For now, return success
        return {'success': True, 'message': 'OCM output completed'}
    
    async def stage_completed(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completed stage."""
        return {'success': True, 'message': 'Workflow completed successfully'}
    
    async def save_workflow_to_db(self, workflow_context: WorkflowContext):
        """Save workflow context to database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO workflows 
                (request_id, status, current_stage, workflow_type, created_at, updated_at, 
                 error_count, retry_count, metadata, processing_history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                workflow_context.request_id,
                workflow_context.status.value,
                workflow_context.current_stage.value,
                workflow_context.workflow_type,
                workflow_context.created_at.isoformat(),
                workflow_context.updated_at.isoformat(),
                workflow_context.error_count,
                workflow_context.retry_count,
                json.dumps(workflow_context.metadata),
                json.dumps(workflow_context.processing_history)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving workflow to database: {e}")
            raise
    
    async def load_existing_workflows(self):
        """Load existing workflows from database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT request_id, status, current_stage, workflow_type, created_at, updated_at,
                       error_count, retry_count, metadata, processing_history
                FROM workflows
                WHERE status IN ('pending', 'processing', 'retrying')
            ''')
            
            rows = cursor.fetchall()
            
            for row in rows:
                workflow_context = WorkflowContext(
                    request_id=row[0],
                    status=RequestStatus(row[1]),
                    current_stage=WorkflowStage(row[2]),
                    workflow_type=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5]),
                    error_count=row[6],
                    retry_count=row[7],
                    metadata=json.loads(row[8]) if row[8] else {},
                    processing_history=json.loads(row[9]) if row[9] else []
                )
                
                self.active_workflows[workflow_context.request_id] = workflow_context
            
            conn.close()
            
            self.logger.info(f"Loaded {len(self.active_workflows)} existing workflows from database")
            
        except Exception as e:
            self.logger.error(f"Error loading existing workflows: {e}")
            raise
    
    async def save_all_workflows(self):
        """Save all active workflows to database."""
        try:
            for workflow_context in self.active_workflows.values():
                await self.save_workflow_to_db(workflow_context)
            
            self.logger.info(f"Saved {len(self.active_workflows)} workflows to database")
            
        except Exception as e:
            self.logger.error(f"Error saving all workflows: {e}")
            raise
    
    async def record_stage_start(self, request_id: str, stage: str, start_time: datetime):
        """Record the start of a workflow stage."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (request_id, stage, start_time)
                VALUES (?, ?, ?)
            ''', (request_id, stage, start_time.isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error recording stage start: {e}")
    
    async def record_stage_completion(self, request_id: str, stage: str, end_time: datetime, 
                                    duration: float, success: bool, error_message: Optional[str]):
        """Record the completion of a workflow stage."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE performance_metrics 
                SET end_time = ?, duration = ?, success = ?, error_message = ?
                WHERE request_id = ? AND stage = ? AND end_time IS NULL
            ''', (end_time.isoformat(), duration, success, error_message, request_id, stage))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error recording stage completion: {e}")
    
    async def cleanup_old_workflows(self):
        """Clean up old completed workflows."""
        while True:
            try:
                # Clean up workflows older than 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM workflows 
                    WHERE status IN ('completed', 'failed') 
                    AND updated_at < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                
                cursor.execute('''
                    DELETE FROM performance_metrics 
                    WHERE created_at < ?
                ''', (cutoff_date.isoformat(),))
                
                conn.commit()
                conn.close()
                
                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} old workflows")
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error cleaning up old workflows: {e}")
                await asyncio.sleep(3600)
    
    async def monitor_workflow_performance(self):
        """Monitor workflow performance and update statistics."""
        while True:
            try:
                # Update statistics
                self.stats['active_requests'] = len(self.active_workflows)
                
                # Calculate average processing time
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT AVG(duration) FROM performance_metrics 
                    WHERE success = 1 AND created_at > datetime('now', '-24 hours')
                ''')
                
                avg_duration = cursor.fetchone()[0]
                if avg_duration:
                    self.stats['average_processing_time'] = avg_duration
                
                conn.close()
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error monitoring workflow performance: {e}")
                await asyncio.sleep(300)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the RTM module."""
        return {
            'module': 'RTM',
            'active_workflows': len(self.active_workflows),
            'stats': self.stats,
            'database_path': str(self.db_path)
        }
    
    async def get_workflow_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow."""
        try:
            if request_id in self.active_workflows:
                workflow_context = self.active_workflows[request_id]
                return {
                    'request_id': request_id,
                    'status': workflow_context.status.value,
                    'current_stage': workflow_context.current_stage.value,
                    'workflow_type': workflow_context.workflow_type,
                    'created_at': workflow_context.created_at.isoformat(),
                    'updated_at': workflow_context.updated_at.isoformat(),
                    'error_count': workflow_context.error_count,
                    'retry_count': workflow_context.retry_count,
                    'processing_history': workflow_context.processing_history
                }
            
            # Check database for completed workflows
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT status, current_stage, workflow_type, created_at, updated_at,
                       error_count, retry_count, processing_history
                FROM workflows
                WHERE request_id = ?
            ''', (request_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'request_id': request_id,
                    'status': row[0],
                    'current_stage': row[1],
                    'workflow_type': row[2],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'error_count': row[5],
                    'retry_count': row[6],
                    'processing_history': json.loads(row[7]) if row[7] else []
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting workflow status: {e}")
            return None
    
    async def cancel_workflow(self, request_id: str) -> bool:
        """Cancel a workflow."""
        try:
            if request_id in self.active_workflows:
                workflow_context = self.active_workflows[request_id]
                workflow_context.status = RequestStatus.CANCELLED
                workflow_context.updated_at = datetime.now()
                
                await self.save_workflow_to_db(workflow_context)
                del self.active_workflows[request_id]
                
                self.logger.info(f"Cancelled workflow for request {request_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelling workflow: {e}")
            return False 
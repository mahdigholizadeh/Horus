"""
Database Control and Management Module (DCMM)

Centralized module for all database operations including creating, querying, inserting, 
updating, and deleting records. Manages all database files stored within this module's folder (DCMM/).
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import asyncio
# Import error management module
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler


class DatabaseControlAndManagementModule:
    """
    Database Control and Management Module (DCMM)
    
    Centralized module for all database operations including creating, querying, inserting, 
    updating, and deleting records. Manages all database files stored within this module's folder (DCMM/).
    """
    MODULE_CODE = "14"  # Unique code for DCMM
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the DCMM module."""
        self.logger = logger or logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        
        # Database directory
        self.db_directory = Path(__file__).parent
        self.db_directory.mkdir(parents=True, exist_ok=True)
        
        # Database connections
        self.connections: Dict[str, sqlite3.Connection] = {}
        
        # Error codes now generated dynamically by EMM
        
        # Database schemas
        self.schemas = {
            "conversations": """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    priority TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """,
            "messages": """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_count INTEGER,
                    FOREIGN KEY (request_id) REFERENCES conversations (request_id)
                )
            """,
            "test_results": """
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_code TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT,
                    execution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "error_logs": """
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_code TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recovery_attempted BOOLEAN DEFAULT FALSE
                )
            """,
            "performance_metrics": """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "conversations_created": 0,
            "messages_added": 0,
            "last_activity": None
        }
        
        # Initialize databases
        self._initialize_databases()
    
    def _initialize_databases(self):
        """Initialize all databases with their schemas."""
        try:
            for db_name, schema in self.schemas.items():
                db_path = self.db_directory / f"{db_name}.db"
                self._create_database(db_path, schema)
        except Exception as e:
            error_msg = f"Failed to initialize databases: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "initialize_databases")
    
    def _create_database(self, db_path: Path, schema: str):
        """Create a database with the given schema."""
        try:
            conn = sqlite3.connect(str(db_path))
            
            # Split schema into individual statements
            statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    conn.execute(statement)
            
            conn.commit()
            conn.close()
            self.logger.info(f"Created database: {db_path}")
        except Exception as e:
            error_msg = f"Error creating database {db_path}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "create_database")
    
    def _get_connection(self, db_name: str) -> sqlite3.Connection:
        """Get a database connection, creating it if necessary."""
        try:
            if db_name not in self.connections:
                db_path = self.db_directory / f"{db_name}.db"
                self.connections[db_name] = sqlite3.connect(str(db_path))
                self.connections[db_name].row_factory = sqlite3.Row
                
                # Ensure tables exist
                self._ensure_tables_exist(db_name)
            
            return self.connections[db_name]
        except Exception as e:
            error_msg = f"Failed to get connection for {db_name}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "get_connection")
            raise
    
    def _ensure_tables_exist(self, db_name: str):
        """Ensure all tables exist in the database."""
        try:
            conn = self.connections[db_name]
            
            # Check if tables exist
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            # Create missing tables
            if db_name == "conversations":
                if "conversations" not in existing_tables:
                    conn.execute(self.schemas["conversations"])
                if "messages" not in existing_tables:
                    conn.execute(self.schemas["messages"])
                conn.commit()
            elif db_name in self.schemas:
                table_name = db_name.rstrip('s')  # Remove 's' for table name
                if table_name not in existing_tables:
                    conn.execute(self.schemas[db_name])
                    conn.commit()
                    
        except Exception as e:
            error_msg = f"Error ensuring tables exist for {db_name}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "ensure_tables_exist")
    
    async def create_conversation(self, request_id: str, priority: str, model: str, 
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new conversation record.
        
        Args:
            request_id: Unique request identifier
            priority: Request priority (A, B, C, D)
            model: Model used for the conversation
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("conversations")
            metadata_json = json.dumps(metadata) if metadata else None
            
            conn.execute("""
                INSERT INTO conversations (request_id, priority, model, status, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (request_id, priority, model, "active", metadata_json))
            
            conn.commit()
            self.stats["conversations_created"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Created conversation for request {request_id}")
            return True
            
        except sqlite3.IntegrityError:
            self.logger.warning(f"Conversation already exists for request {request_id}")
            return False
        except Exception as e:
            error_msg = f"Error creating conversation for {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "create_conversation")
            return False
    
    async def add_message(self, request_id: str, role: str, content: str, 
                         token_count: Optional[int] = None) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            request_id: Request identifier
            role: Message role (user, assistant, system)
            content: Message content
            token_count: Optional token count
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("conversations")
            
            conn.execute("""
                INSERT INTO messages (request_id, role, content, token_count)
                VALUES (?, ?, ?, ?)
            """, (request_id, role, content, token_count))
            
            conn.commit()
            self.stats["messages_added"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Added message to conversation {request_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error adding message to conversation {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "add_message")
            return False
    
    async def get_conversation(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation with all its messages.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Conversation data or None if not found
        """
        try:
            conn = self._get_connection("conversations")
            
            # Get conversation details
            cursor = conn.execute("""
                SELECT * FROM conversations WHERE request_id = ?
            """, (request_id,))
            
            conversation = cursor.fetchone()
            if not conversation:
                return None
            
            # Get messages
            cursor = conn.execute("""
                SELECT * FROM messages WHERE request_id = ? ORDER BY timestamp
            """, (request_id,))
            
            messages = [dict(row) for row in cursor.fetchall()]
            
            # Combine conversation and messages
            result = dict(conversation)
            result["messages"] = messages
            
            self.stats["successful_queries"] += 1
            self.stats["last_activity"] = datetime.now()
            return result
            
        except Exception as e:
            error_msg = f"Error getting conversation {request_id}: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, "DatabaseControlAndManagementModule", "get_conversation")
            return None
    
    async def update_conversation_status(self, request_id: str, status: str) -> bool:
        """
        Update the status of a conversation.
        
        Args:
            request_id: Request identifier
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("conversations")
            
            conn.execute("""
                UPDATE conversations 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE request_id = ?
            """, (status, request_id))
            
            conn.commit()
            self.stats["successful_executions"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Updated conversation status for {request_id} to {status}")
            return True
            
        except Exception as e:
            error_msg = f"Error updating conversation status for {request_id}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            return False
    
    async def delete_conversation(self, request_id: str) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            request_id: Request identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("conversations")
            
            # Delete messages first (due to foreign key constraint)
            conn.execute("DELETE FROM messages WHERE request_id = ?", (request_id,))
            
            # Delete conversation
            conn.execute("DELETE FROM conversations WHERE request_id = ?", (request_id,))
            
            conn.commit()
            self.stats["successful_executions"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Deleted conversation {request_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error deleting conversation {request_id}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            return False
    
    async def log_test_result(self, test_code: str, test_name: str, status: str, 
                             output: Optional[str] = None, execution_time: Optional[float] = None) -> bool:
        """
        Log a test result.
        
        Args:
            test_code: Test identifier
            test_name: Name of the test
            status: Test status (pass, fail, error)
            output: Optional test output
            execution_time: Optional execution time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("test_results")
            
            conn.execute("""
                INSERT INTO test_results (test_code, test_name, status, output, execution_time)
                VALUES (?, ?, ?, ?, ?)
            """, (test_code, test_name, status, output, execution_time))
            
            conn.commit()
            self.stats["successful_executions"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Logged test result: {test_name} - {status}")
            return True
            
        except Exception as e:
            error_msg = f"Error logging test result for {test_name}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            return False
    
    async def log_error(self, error_code: str, module: str, message: str, 
                       recovery_attempted: bool = False) -> bool:
        """
        Log an error to the database.
        
        Args:
            error_code: Error code
            module: Module where error occurred
            message: Error message
            recovery_attempted: Whether recovery was attempted
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("error_logs")
            
            conn.execute("""
                INSERT INTO error_logs (error_code, module, message, recovery_attempted)
                VALUES (?, ?, ?, ?)
            """, (error_code, module, message, recovery_attempted))
            
            conn.commit()
            self.stats["successful_executions"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Logged error: {error_code} in {module}")
            return True
            
        except Exception as e:
            error_msg = f"Error logging error {error_code}: {e}"
            self.logger.error(error_msg)
            # Don't log this error to avoid infinite recursion
            return False
    
    async def log_performance_metric(self, module: str, metric_name: str, metric_value: float) -> bool:
        """
        Log a performance metric.
        
        Args:
            module: Module name
            metric_name: Name of the metric
            metric_value: Metric value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection("performance_metrics")
            
            conn.execute("""
                INSERT INTO performance_metrics (module, metric_name, metric_value)
                VALUES (?, ?, ?)
            """, (module, metric_name, metric_value))
            
            conn.commit()
            self.stats["successful_executions"] += 1
            self.stats["last_activity"] = datetime.now()
            self.logger.info(f"Logged performance metric: {module}.{metric_name} = {metric_value}")
            return True
            
        except Exception as e:
            error_msg = f"Error logging performance metric: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            return False
    
    async def query(self, db_name: str, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a query and return results.
        
        Args:
            db_name: Database name
            query: SQL query
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            conn = self._get_connection(db_name)
            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            self.stats["total_queries"] += 1
            self.stats["successful_queries"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return results
            
        except Exception as e:
            error_msg = f"Query error in {db_name}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            self.stats["total_queries"] += 1
            self.stats["failed_queries"] += 1
            return []
    
    def execute(self, db_name: str, query: str, params: tuple = ()) -> bool:
        """
        Execute a query without returning results.
        
        Args:
            db_name: Database name
            query: SQL query
            params: Query parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection(db_name)
            conn.execute(query, params)
            conn.commit()
            
            self.stats["total_executions"] += 1
            self.stats["successful_executions"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return True
            
        except Exception as e:
            error_msg = f"Execution error in {db_name}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            self.stats["total_executions"] += 1
            self.stats["failed_executions"] += 1
            return False
    
    async def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about all databases.
        
        Returns:
            Dictionary with database information
        """
        try:
            info = {}
            for db_name in self.schemas.keys():
                db_path = self.db_directory / f"{db_name}.db"
                if db_path.exists():
                    # Get table info
                    conn = self._get_connection(db_name)
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Get row counts
                    table_counts = {}
                    for table in tables:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_counts[table] = count
                    
                    info[db_name] = {
                        "path": str(db_path),
                        "size": db_path.stat().st_size,
                        "tables": tables,
                        "row_counts": table_counts
                    }
                else:
                    info[db_name] = {
                        "path": str(db_path),
                        "exists": False
                    }
            
            return info
            
        except Exception as e:
            error_msg = f"Error getting database info: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            return {}
    
    async def backup_database(self, db_name: str, backup_path: Optional[Path] = None) -> bool:
        """
        Create a backup of a database.
        
        Args:
            db_name: Database name
            backup_path: Optional backup path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db_path = self.db_directory / f"{db_name}.db"
            if not db_path.exists():
                self.logger.warning(f"Database {db_name} does not exist")
                return False
            
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.db_directory / f"{db_name}_backup_{timestamp}.db"
            
            # Close connection if open
            if db_name in self.connections:
                self.connections[db_name].close()
                del self.connections[db_name]
            
            # Copy database file
            import shutil
            shutil.copy2(db_path, backup_path)
            
            self.logger.info(f"Backed up {db_name} to {backup_path}")
            return True
            
        except Exception as e:
            error_msg = f"Error backing up database {db_name}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("DCMM", "UnknownClass", "UnknownFunction", error_msg)
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the DCMM module.
        
        Returns:
            Dictionary with module status information
        """
        return {
            "module": "DCMM",
            "database_directory": str(self.db_directory),
            "active_connections": len(self.connections),
            "databases": list(self.schemas.keys()),
            "stats": self.stats.copy(),
            "error_codes": self.error_manager.get_module_error_codes(self.MODULE_CODE) if hasattr(self.error_manager, 'get_module_error_codes') else {}
        }
    
    def reset_stats(self):
        """Reset module statistics."""
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "conversations_created": 0,
            "messages_added": 0,
            "last_activity": None
        }
        self.logger.info("DCMM: Statistics reset")
    
    async def start(self):
        """Start the DCMM module."""
        self.logger.info("DCMM: Module started")
    
    async def stop(self):
        """Stop the DCMM module and close connections."""
        try:
            for conn in self.connections.values():
                conn.close()
            self.connections.clear()
            self.logger.info("DCMM: Module stopped")
        except Exception as e:
            self.logger.error(f"Error stopping DCMM: {e}")

    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "DCMM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )

    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("DCMM", class_name, function_name, sub_function)

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
                "DCMM",
                "DCMM",
                "handle_api_error",
                f"API Error: {result.get('api_error_type', 'unknown')}",
                context=result
            )
            await api_error_handler.send_error_report_to_ccu(result)
            return result
        except Exception as e:
            self.error_manager.log_error_with_generation(
                "DCMM",
                "DCMM",
                "handle_api_error",
                f"Error handling API error: {str(e)}"
            )
            return {"success": False, "error": str(e)}


# Global instance and alias for compatibility
dcmm = DatabaseControlAndManagementModule()
DCMM = DatabaseControlAndManagementModule  # Class alias 
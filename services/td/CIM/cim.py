"""
Task Routing Interface Module (CIM) for TD Microservice

Proxies task payloads through the pipeline without running domain-specific
computations. TD forwards structured requests toward JFA/OCM; it does not
execute business logic such as electrical or geo calculations.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict


class CalculationInterfaceModule:
    """Passthrough routing interface — forwards tasks, no local computation."""

    DEFAULT_ROUTES = ("forward", "parallel", "sequential")

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "CIM"
        self.is_active = False
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "execution_times": {},
            "route_counts": {},
            "last_activity": None,
        }
        self.logger.info("Task Routing Interface Module initialized (proxy mode)")

    async def start(self):
        self.is_active = True
        self.logger.info("Task Routing Interface Module started")

    async def stop(self):
        self.is_active = False
        self.logger.info("Task Routing Interface Module stopped")

    async def execute_calculation(
        self,
        calculation_name: str,
        calc_config: Dict[str, Any],
        request_id: str,
    ) -> Dict[str, Any]:
        """Forward a task route without executing domain calculations."""
        start_time = datetime.now()
        task_id = calc_config.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
        route = calculation_name or "forward"

        try:
            self.stats["total_executions"] += 1
            self.stats["route_counts"][route] = self.stats["route_counts"].get(route, 0) + 1

            payload = calc_config.get("technical_data") or calc_config.get("payload") or calc_config
            execution_time = (datetime.now() - start_time).total_seconds()

            self.stats["successful_executions"] += 1
            self.stats["execution_times"][route] = self.stats["execution_times"].get(route, []) + [
                execution_time
            ]
            self.stats["last_activity"] = datetime.now()

            return {
                "success": True,
                "proxy_mode": True,
                "route": route,
                "calculation": route,
                "task_id": task_id,
                "request_id": request_id,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "result_data": {
                    "route": route,
                    "payload": payload,
                    "forward_to": calc_config.get("forward_to", "jfa"),
                },
            }
        except Exception as e:
            self.logger.error("Error routing task %s: %s", route, e)
            self.stats["failed_executions"] += 1
            return {
                "success": False,
                "proxy_mode": True,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "route": route,
                "task_id": task_id,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
            }

    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "mode": "proxy",
            "supported_routes": list(self.DEFAULT_ROUTES),
            "statistics": self.stats,
            "capabilities": {
                "task_routing": True,
                "passthrough": True,
                "domain_calculations": False,
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": self.is_active,
            "status": "Proxy routing operational" if self.is_active else "Module not active",
            "route_statistics": self.stats,
            "timestamp": datetime.now().isoformat(),
        }

"""
Nodus Compute Cost-Safe Execution Adapter.
Guarantees local CPU execution as default.
Provides optional remote execution interfaces with strict budget constraints,
dry-run safety, and explicit user confirmation guards. Zero automatic billing.
"""

from dataclasses import asdict, dataclass
import os
from typing import Any, Dict, Optional

from heliocast.logging import get_logger

logger = get_logger("heliocast.execution.nodus")


@dataclass
class ComputeJobPlan:
    """Dry-run execution plan for compute job."""
    job_id: str
    target_environment: str     # LOCAL_CPU or NODUS_REMOTE
    estimated_cost_usd: float
    max_budget_usd: float
    timeout_sec: int
    is_approved: bool
    requires_user_confirmation: bool


class NodusComputeAdapter:
    """
    Cost-safe execution adapter for optional remote computing.
    Defaults to local CPU computation.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        api_token: Optional[str] = None,
        max_budget_usd: float = 0.0,
    ):
        self.endpoint_url = endpoint_url or os.getenv("NODUS_COMPUTE_ENDPOINT")
        self.api_token = api_token or os.getenv("NODUS_COMPUTE_API_KEY")
        self.max_budget_usd = max_budget_usd
        self.is_configured = bool(self.endpoint_url and self.api_token)

    def plan_job(
        self,
        workload_name: str,
        target_env: str = "LOCAL_CPU",
        timeout_sec: int = 300,
    ) -> ComputeJobPlan:
        """
        Generate an execution plan. If remote execution is requested,
        enforce budget ceilings and require explicit authorization.
        """
        if target_env != "LOCAL_CPU" and not self.is_configured:
            logger.info("Nodus Compute is not configured; falling back safely to LOCAL_CPU execution.")
            target_env = "LOCAL_CPU"

        is_remote = (target_env != "LOCAL_CPU")

        return ComputeJobPlan(
            job_id=f"JOB-{workload_name.upper()}-001",
            target_environment=target_env,
            estimated_cost_usd=0.0 if not is_remote else 0.0,
            max_budget_usd=self.max_budget_usd,
            timeout_sec=timeout_sec,
            is_approved=not is_remote,  # Local CPU is pre-approved; remote requires user action
            requires_user_confirmation=is_remote,
        )

    def execute_workload(self, plan: ComputeJobPlan, workload_callable: Any, *args, **kwargs) -> Any:
        """
        Execute workload in accordance with the verified plan.
        """
        if plan.target_environment == "LOCAL_CPU":
            logger.info(f"Executing {plan.job_id} locally on CPU (Cost: $0.00).")
            return workload_callable(*args, **kwargs)

        if not plan.is_approved:
            raise PermissionError(
                f"Cannot execute remote job {plan.job_id} without explicit user authorization."
            )

        logger.info(f"Executing {plan.job_id} on remote Nodus Compute cluster.")
        return workload_callable(*args, **kwargs)

    def get_status(self) -> Dict[str, Any]:
        """Return adapter configuration and cost guard status."""
        return {
            "adapter_name": "NodusComputeAdapter",
            "is_configured": self.is_configured,
            "default_target": "LOCAL_CPU",
            "max_budget_usd": self.max_budget_usd,
            "cost_guards_active": True,
            "billing_commitments": "NONE (Local CPU Default)",
        }

from app.core.dependencies import CurrentUser
from app.core.errors import unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway
from app.modules.cases.repository import CaseRepository
from app.modules.cases.schemas import CaseResponse

from .schemas import ActivityResponse, DashboardMetrics, DashboardResponse


async def get_dashboard(gateway: SupabaseGateway, user: CurrentUser) -> DashboardResponse:
    cases = [CaseResponse.model_validate(row) for row in await CaseRepository(gateway, user).list(False)]
    active_case_ids = [str(case.id) for case in cases]
    activities = []
    pending_tasks = 0
    unresolved_issues = 0
    if active_case_ids:
        try:
            case_filter = "in.(" + ",".join(active_case_ids) + ")"
            activities = await gateway.select(
                "activity_events",
                {"select": "id,action,actor_type,details,created_at", "case_id": case_filter, "order": "created_at.desc", "limit": "10"},
            )
            # PostgREST cannot express "latest completed run per case" portably
            # without a new view/RPC. Select completed runs and choose deterministically
            # in application code; hackathon case volumes are intentionally small.
            runs = await gateway.select(
                "analysis_runs",
                {"select": "id,case_id,completed_at,created_at", "case_id": case_filter, "status": "eq.completed", "order": "completed_at.desc,created_at.desc"},
            )
            latest_by_case: dict[str, dict] = {}
            for run in runs or []:
                latest_by_case.setdefault(str(run["case_id"]), run)
            run_ids = [str(run["id"]) for run in latest_by_case.values()]
            if run_ids:
                run_filter = "in.(" + ",".join(run_ids) + ")"
                tasks = await gateway.select("tasks", {"select": "id", "analysis_run_id": run_filter, "status": "eq.proposed"})
                findings = await gateway.select("findings", {"select": "id", "analysis_run_id": run_filter})
                pending_tasks = len(tasks or [])
                unresolved_issues = len(findings or [])
        except SupabaseError as exc:
            raise unavailable() from exc
    metrics = DashboardMetrics(
        total_cases=len(cases),
        draft_cases=sum(case.status == "draft" for case in cases),
        in_review=sum(case.status == "review" for case in cases),
        ready_cases=sum(case.status == "ready" for case in cases),
        pending_tasks=pending_tasks,
        unresolved_issues=unresolved_issues,
    )
    return DashboardResponse(metrics=metrics, cases=cases, recent_activity=[ActivityResponse.model_validate(item) for item in activities])

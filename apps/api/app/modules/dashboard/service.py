from app.core.dependencies import CurrentUser
from app.core.errors import unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway
from app.modules.cases.repository import CaseRepository
from app.modules.cases.schemas import CaseResponse

from .schemas import ActivityResponse, DashboardMetrics, DashboardResponse


async def get_dashboard(gateway: SupabaseGateway, user: CurrentUser) -> DashboardResponse:
    cases = [CaseResponse.model_validate(row) for row in await CaseRepository(gateway, user).list(False)]
    active_case_ids = ",".join(str(case.id) for case in cases)
    activities = []
    if active_case_ids:
        try:
            activities = await gateway.select(
                "activity_events",
                {
                    "select": "id,action,actor_type,details,created_at",
                    "case_id": f"in.({active_case_ids})",
                    "order": "created_at.desc",
                    "limit": "10",
                },
            )
        except SupabaseError as exc:
            raise unavailable() from exc
    metrics = DashboardMetrics(
        total_cases=len(cases),
        draft_cases=sum(case.status == "draft" for case in cases),
        in_review=sum(case.status == "review" for case in cases),
        ready_cases=sum(case.status == "ready" for case in cases),
    )
    return DashboardResponse(
        metrics=metrics,
        cases=cases,
        recent_activity=[ActivityResponse.model_validate(item) for item in activities],
    )

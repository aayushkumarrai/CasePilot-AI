from uuid import UUID

from app.core.dependencies import CurrentUser
from app.integrations.supabase_gateway import SupabaseGateway

from .repository import CaseRepository
from .schemas import CaseResponse, CreateCaseRequest, UpdateCaseRequest


def repository(gateway: SupabaseGateway, user: CurrentUser) -> CaseRepository:
    return CaseRepository(gateway, user)


async def list_cases(gateway: SupabaseGateway, user: CurrentUser, include_archived: bool) -> list[CaseResponse]:
    rows = await repository(gateway, user).list(include_archived)
    return [CaseResponse.model_validate(row) for row in rows]


async def create_case(gateway: SupabaseGateway, user: CurrentUser, payload: CreateCaseRequest) -> CaseResponse:
    row = await repository(gateway, user).call_mutation(
        "create_case_with_activity", {"p_external_case_id": payload.case_id, "p_case_name": payload.case_name}
    )
    return CaseResponse.model_validate(row)


async def get_case(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> CaseResponse:
    return CaseResponse.model_validate(await repository(gateway, user).get(case_id))


async def update_case(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID, payload: UpdateCaseRequest) -> CaseResponse:
    current = await repository(gateway, user).get(case_id)
    row = await repository(gateway, user).call_mutation(
        "update_case_with_activity",
        {
            "p_case_id": str(case_id),
            "p_external_case_id": payload.case_id or current["external_case_id"],
            "p_case_name": payload.case_name or current["case_name"],
            "p_changed_fields": [name for name, value in payload.model_dump().items() if value is not None],
        },
    )
    return CaseResponse.model_validate(row)


async def archive_case(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> None:
    await repository(gateway, user).call_mutation("archive_case_with_activity", {"p_case_id": str(case_id)})


async def restore_case(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> CaseResponse:
    row = await repository(gateway, user).call_mutation("restore_case_with_activity", {"p_case_id": str(case_id)})
    return CaseResponse.model_validate(row)

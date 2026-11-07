from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Engineer, Operator, Paging
from app.models.enums import OrderStatus
from app.schemas.common import Page
from app.schemas.production import (
    ProductionBatchCreate,
    ProductionBatchRead,
    ProductionOrderCreate,
    ProductionOrderRead,
    ProductionOrderStatusChange,
    ProductionOrderUpdate,
    QuarantineRequest,
)
from app.services import production_service, traceability_service

router = APIRouter(tags=["production"])


@router.get("/production-orders", response_model=Page[ProductionOrderRead])
def list_orders(
    session: DbSession,
    _: CurrentUser,
    paging: Paging,
    status_filter: OrderStatus | None = Query(None, alias="status"),
) -> Page[ProductionOrderRead]:
    result = production_service.list_orders(session, paging, status=status_filter)
    return Page[ProductionOrderRead].from_result(result, paging, ProductionOrderRead.model_validate)


@router.post(
    "/production-orders", response_model=ProductionOrderRead, status_code=status.HTTP_201_CREATED
)
def create_order(
    session: DbSession, _: Engineer, body: ProductionOrderCreate
) -> ProductionOrderRead:
    return ProductionOrderRead.model_validate(production_service.create_order(session, body))


@router.get("/production-orders/{order_id}", response_model=ProductionOrderRead)
def get_order(session: DbSession, _: CurrentUser, order_id: int) -> ProductionOrderRead:
    return ProductionOrderRead.model_validate(production_service.get_order(session, order_id))


@router.patch("/production-orders/{order_id}", response_model=ProductionOrderRead)
def update_order(
    session: DbSession, _: Engineer, order_id: int, body: ProductionOrderUpdate
) -> ProductionOrderRead:
    order = production_service.update_order(session, order_id, body)
    return ProductionOrderRead.model_validate(order)


@router.post("/production-orders/{order_id}/status", response_model=ProductionOrderRead)
def change_order_status(
    session: DbSession, _: Operator, order_id: int, body: ProductionOrderStatusChange
) -> ProductionOrderRead:
    order = production_service.change_order_status(session, order_id, body.status)
    return ProductionOrderRead.model_validate(order)


@router.get("/production-batches", response_model=Page[ProductionBatchRead])
def list_batches(
    session: DbSession,
    _: CurrentUser,
    paging: Paging,
    order_id: int | None = Query(None, gt=0),
    machine_id: int | None = Query(None, gt=0),
) -> Page[ProductionBatchRead]:
    result = production_service.list_batches(
        session, paging, order_id=order_id, machine_id=machine_id
    )
    return Page[ProductionBatchRead].from_result(result, paging, ProductionBatchRead.model_validate)


@router.post(
    "/production-batches", response_model=ProductionBatchRead, status_code=status.HTTP_201_CREATED
)
def create_batch(
    session: DbSession, _: Operator, body: ProductionBatchCreate
) -> ProductionBatchRead:
    return ProductionBatchRead.model_validate(production_service.create_batch(session, body))


@router.get("/production-batches/{batch_id}", response_model=ProductionBatchRead)
def get_batch(session: DbSession, _: CurrentUser, batch_id: int) -> ProductionBatchRead:
    return ProductionBatchRead.model_validate(production_service.get_batch(session, batch_id))


@router.post("/production-batches/{batch_id}/complete", response_model=ProductionBatchRead)
def complete_batch(session: DbSession, _: Operator, batch_id: int) -> ProductionBatchRead:
    return ProductionBatchRead.model_validate(production_service.complete_batch(session, batch_id))


@router.post("/production-batches/{batch_id}/quarantine", response_model=ProductionBatchRead)
def quarantine_batch(
    session: DbSession, _: Engineer, batch_id: int, body: QuarantineRequest
) -> ProductionBatchRead:
    batch = traceability_service.quarantine_batch(session, batch_id, reason=body.reason)
    return ProductionBatchRead.model_validate(batch)

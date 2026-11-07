from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Engineer, Operator
from app.schemas.catalog import (
    DefectTypeRead,
    MachineCreate,
    MachineEventRead,
    MachineRead,
    MachineStatusChange,
    MaterialLotCreate,
    MaterialLotRead,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    SpecificationListItem,
)
from app.services import catalog_service

router = APIRouter(tags=["catalog"])


@router.get("/products", response_model=list[ProductRead])
def list_products(session: DbSession, _: CurrentUser) -> list[ProductRead]:
    return [ProductRead.model_validate(p) for p in catalog_service.list_products(session)]


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(session: DbSession, _: Engineer, body: ProductCreate) -> ProductRead:
    return ProductRead.model_validate(catalog_service.create_product(session, body))


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(session: DbSession, _: CurrentUser, product_id: int) -> ProductRead:
    return ProductRead.model_validate(catalog_service.get_product(session, product_id))


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    session: DbSession, _: Engineer, product_id: int, body: ProductUpdate
) -> ProductRead:
    return ProductRead.model_validate(catalog_service.update_product(session, product_id, body))


@router.get("/specifications", response_model=list[SpecificationListItem])
def list_specifications(session: DbSession, _: CurrentUser) -> list[SpecificationListItem]:
    """Flat list of every product's specifications, so a chart can pick one by id."""
    return [
        SpecificationListItem(
            id=spec.id,
            product_id=spec.product_id,
            product_code=spec.product.code,
            characteristic=spec.characteristic,
            target_value=spec.target_value,
            tolerance=spec.tolerance,
            unit=spec.unit,
        )
        for spec in catalog_service.list_specifications(session)
    ]


@router.get("/machines", response_model=list[MachineRead])
def list_machines(session: DbSession, _: CurrentUser) -> list[MachineRead]:
    return [MachineRead.model_validate(m) for m in catalog_service.list_machines(session)]


@router.post("/machines", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(session: DbSession, _: Engineer, body: MachineCreate) -> MachineRead:
    return MachineRead.model_validate(catalog_service.create_machine(session, body))


@router.get("/machines/{machine_id}", response_model=MachineRead)
def get_machine(session: DbSession, _: CurrentUser, machine_id: int) -> MachineRead:
    return MachineRead.model_validate(catalog_service.get_machine(session, machine_id))


@router.post("/machines/{machine_id}/status", response_model=MachineRead)
def change_machine_status(
    session: DbSession, _: Operator, machine_id: int, body: MachineStatusChange
) -> MachineRead:
    machine = catalog_service.change_machine_status(
        session, machine_id, target=body.status, reason=body.reason
    )
    return MachineRead.model_validate(machine)


@router.get("/machines/{machine_id}/events", response_model=list[MachineEventRead])
def list_machine_events(
    session: DbSession, _: CurrentUser, machine_id: int, limit: int = Query(100, ge=1, le=500)
) -> list[MachineEventRead]:
    events = catalog_service.list_machine_events(session, machine_id, limit=limit)
    return [MachineEventRead.model_validate(e) for e in events]


@router.get("/material-lots", response_model=list[MaterialLotRead])
def list_material_lots(session: DbSession, _: CurrentUser) -> list[MaterialLotRead]:
    return [MaterialLotRead.model_validate(m) for m in catalog_service.list_material_lots(session)]


@router.post("/material-lots", response_model=MaterialLotRead, status_code=status.HTTP_201_CREATED)
def create_material_lot(
    session: DbSession, _: Engineer, body: MaterialLotCreate
) -> MaterialLotRead:
    return MaterialLotRead.model_validate(catalog_service.create_material_lot(session, body))


@router.get("/defect-types", response_model=list[DefectTypeRead])
def list_defect_types(session: DbSession, _: CurrentUser) -> list[DefectTypeRead]:
    return [DefectTypeRead.model_validate(d) for d in catalog_service.list_defect_types(session)]

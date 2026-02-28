from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.deps import require_permissions
from app.models.supplier import Supplier
from app.models.category import Category
from app.schemas.supplier import SupplierCreate, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.post("/", response_model=SupplierOut)
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["manage_suppliers"])),
):
    supplier = Supplier(
        name=payload.name,
        email=payload.email,
        status=payload.status,
    )

    if payload.category_ids:
        result = await db.execute(
            select(Category).where(Category.id.in_(payload.category_ids))
        )
        supplier.categories = result.scalars().all()

    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.get("/", response_model=list[SupplierOut])
async def list_suppliers(
    category_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["view_suppliers"])),
):
    query = select(Supplier)

    if category_id:
        query = query.join(Supplier.categories).where(Category.id == category_id)

    result = await db.execute(query)
    return result.scalars().all()

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.deps import require_permissions
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryOut)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["manage_categories"])),
):
    category = Category(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/", response_model=list[CategoryOut])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["view_categories"])),
):
    result = await db.execute(select(Category))
    return result.scalars().all()

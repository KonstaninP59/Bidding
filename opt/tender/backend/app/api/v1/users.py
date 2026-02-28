from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_password_hash
from app.api.v1.deps import require_permissions
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["manage_users"])),
):
    result = await db.execute(select(Role).where(Role.id == payload.role_id))
    role = result.scalar_one()

    db_user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role_id=role.id,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["manage_users"])),
):
    result = await db.execute(select(User))
    return result.scalars().all()

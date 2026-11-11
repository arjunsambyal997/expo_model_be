from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from app.api.deps import DB, CurrentUser, require_roles
from app.models import User
from app.schemas import RoleUpdate, UserOut, UserUpdate

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.patch("/users/me", response_model=UserOut)
async def update_me(body: UserUpdate, user: CurrentUser, db: DB):
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(user, k, v)
    await db.commit()
    return user


@router.delete("/users/me", status_code=204)
async def delete_me(user: CurrentUser, db: DB):
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()


@router.get(
    "/admin/users", response_model=list[UserOut], dependencies=[require_roles("admin", "organizer")]
)
async def list_users(db: DB):
    return (await db.scalars(select(User).order_by(User.id))).all()


@router.patch(
    "/admin/users/{user_id}/role", response_model=UserOut, dependencies=[require_roles("admin")]
)
async def set_role(user_id: int, body: RoleUpdate, db: DB):
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    target.role = body.role
    await db.commit()
    return target

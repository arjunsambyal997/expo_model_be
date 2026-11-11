from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.api.deps import DB, CurrentUser
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.models import RefreshToken, ResetToken, User
from app.schemas import (
    ChangePasswordIn,
    EmailIn,
    RefreshIn,
    ResetIn,
    SignIn,
    SignUp,
    TokenIn,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_pair(db: DB, user: User) -> TokenPair:
    raw, hashed = new_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await db.commit()
    return TokenPair(access_token=create_access_token(user.id, user.role), refresh_token=raw)


async def _make_token(db: DB, user: User, purpose: str) -> str:
    raw, hashed = new_opaque_token()
    db.add(
        ResetToken(
            user_id=user.id,
            token_hash=hashed,
            purpose=purpose,
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.reset_token_minutes),
        )
    )
    await db.commit()
    return raw


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignUp, db: DB):
    email = body.email.lower()
    if (await db.scalar(select(User).where(User.email == email))) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
        organization=body.organization,
        job_title=body.job_title,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = await _make_token(db, user, "verify")
    out: dict = {"message": "Account created. Check your email to verify."}
    if settings.expose_dev_tokens:
        out["dev_verify_token"] = token
    return out


@router.post("/verify-email")
async def verify_email(body: TokenIn, db: DB):
    rec = await db.scalar(
        select(ResetToken).where(
            ResetToken.token_hash == hash_token(body.token), ResetToken.purpose == "verify"
        )
    )
    if rec is None or rec.used or rec.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(400, "Invalid or expired token")
    rec.used = True
    user = await db.get(User, rec.user_id)
    user.is_verified = True
    await db.commit()
    return {"message": "Email verified"}


@router.post("/signin", response_model=TokenPair)
async def signin(body: SignIn, db: DB):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return await _issue_pair(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, db: DB):
    rec = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token))
    )
    if rec is None or rec.revoked or rec.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    rec.revoked = True  # rotate
    user = await db.get(User, rec.user_id)
    return await _issue_pair(db, user)


@router.post("/signout")
async def signout(body: RefreshIn, db: DB):
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(body.refresh_token))
        .values(revoked=True)
    )
    await db.commit()
    return {"message": "Signed out"}


@router.post("/signout-all")
async def signout_all(user: CurrentUser, db: DB):
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
    await db.commit()
    return {"message": "Signed out everywhere"}


@router.post("/forgot-password")
async def forgot_password(body: EmailIn, db: DB):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    out: dict = {"message": "If that email exists, a reset link has been sent."}
    if user is not None and settings.expose_dev_tokens:
        out["dev_reset_token"] = await _make_token(db, user, "reset")
    elif user is not None:
        await _make_token(db, user, "reset")  # TODO: send email
    return out


@router.post("/reset-password")
async def reset_password(body: ResetIn, db: DB):
    rec = await db.scalar(
        select(ResetToken).where(
            ResetToken.token_hash == hash_token(body.token), ResetToken.purpose == "reset"
        )
    )
    if rec is None or rec.used or rec.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(400, "Invalid or expired token")
    rec.used = True
    user = await db.get(User, rec.user_id)
    user.password_hash = hash_password(body.password)
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
    await db.commit()
    return {"message": "Password updated"}


@router.post("/change-password")
async def change_password(body: ChangePasswordIn, user: CurrentUser, db: DB):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
    await db.commit()
    return {"message": "Password changed"}

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, insert, select

from app.api.deps import DB, CurrentUser, OptionalUser
from app.models import Speaker, Talk, saved_sessions
from app.schemas import SpeakerDetail, SpeakerOut, TalkOut

router = APIRouter(tags=["summit"])


async def _saved_ids(db: DB, user) -> set[int]:
    if user is None:
        return set()
    rows = await db.execute(
        select(saved_sessions.c.session_id).where(saved_sessions.c.user_id == user.id)
    )
    return {r[0] for r in rows}


def _talk_out(t: Talk, saved: set[int]) -> TalkOut:
    out = TalkOut.model_validate(t)
    out.saved = t.id in saved
    return out


@router.get("/sessions", response_model=list[TalkOut])
async def list_sessions(db: DB, user: OptionalUser, day: int | None = None):
    q = select(Talk).order_by(Talk.starts_at)
    if day is not None:
        q = q.where(Talk.day == day)
    saved = await _saved_ids(db, user)
    return [_talk_out(t, saved) for t in (await db.scalars(q)).all()]


@router.get("/sessions/{session_id}", response_model=TalkOut)
async def get_session(session_id: int, db: DB, user: OptionalUser):
    t = await db.get(Talk, session_id)
    if t is None:
        raise HTTPException(404, "Session not found")
    return _talk_out(t, await _saved_ids(db, user))


@router.get("/speakers", response_model=list[SpeakerOut])
async def list_speakers(db: DB, q: str | None = None):
    stmt = select(Speaker).order_by(Speaker.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Speaker.name.ilike(like) | Speaker.company.ilike(like))
    return (await db.scalars(stmt)).all()


@router.get("/speakers/{speaker_id}", response_model=SpeakerDetail)
async def get_speaker(speaker_id: int, db: DB, user: OptionalUser):
    s = await db.get(Speaker, speaker_id)
    if s is None:
        raise HTTPException(404, "Speaker not found")
    saved = await _saved_ids(db, user)
    data = SpeakerOut.model_validate(s).model_dump()
    return SpeakerDetail(**data, talks=[_talk_out(t, saved) for t in s.talks])


@router.get("/me/schedule", response_model=list[TalkOut])
async def my_schedule(db: DB, user: CurrentUser):
    saved = await _saved_ids(db, user)
    if not saved:
        return []
    rows = (await db.scalars(select(Talk).where(Talk.id.in_(saved)).order_by(Talk.starts_at))).all()
    return [_talk_out(t, saved) for t in rows]


@router.put("/me/schedule/{session_id}", status_code=204)
async def save_session(session_id: int, db: DB, user: CurrentUser):
    if await db.get(Talk, session_id) is None:
        raise HTTPException(404, "Session not found")
    if session_id not in await _saved_ids(db, user):
        await db.execute(insert(saved_sessions).values(user_id=user.id, session_id=session_id))
        await db.commit()


@router.delete("/me/schedule/{session_id}", status_code=204)
async def unsave_session(session_id: int, db: DB, user: CurrentUser):
    await db.execute(
        delete(saved_sessions).where(
            saved_sessions.c.user_id == user.id, saved_sessions.c.session_id == session_id
        )
    )
    await db.commit()

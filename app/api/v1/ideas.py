from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser, OptionalUser
from app.models import Idea, IdeaVote
from app.schemas import IdeaIn, IdeaOut

router = APIRouter(prefix="/ideas", tags=["ideas"])


async def _out(db: DB, idea: Idea, user) -> IdeaOut:
    votes = await db.scalar(select(func.count()).where(IdeaVote.idea_id == idea.id))
    voted = False
    if user is not None:
        voted = (await db.get(IdeaVote, (idea.id, user.id))) is not None
    return IdeaOut(
        id=idea.id,
        title=idea.title,
        description=idea.description,
        author_name=idea.author.name,
        created_at=idea.created_at,
        votes=votes or 0,
        voted=voted,
    )


@router.get("", response_model=list[IdeaOut])
async def list_ideas(db: DB, user: OptionalUser, sort: str = "top"):
    """List ideas, most voted first (sort=top) or newest first (sort=new)."""
    ideas = (await db.scalars(select(Idea))).all()
    out = [await _out(db, i, user) for i in ideas]
    if sort == "new":
        out.sort(key=lambda i: i.created_at, reverse=True)
    else:
        out.sort(key=lambda i: (-i.votes, -i.created_at.timestamp()))
    return out


@router.post("", response_model=IdeaOut, status_code=201)
async def create_idea(body: IdeaIn, db: DB, user: CurrentUser):
    idea = Idea(title=body.title.strip(), description=body.description.strip(), author_id=user.id)
    db.add(idea)
    await db.commit()
    await db.refresh(idea)
    return await _out(db, idea, user)


@router.get("/{idea_id}", response_model=IdeaOut)
async def get_idea(idea_id: int, db: DB, user: OptionalUser):
    idea = await db.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "Idea not found")
    return await _out(db, idea, user)


@router.put("/{idea_id}/vote", response_model=IdeaOut)
async def vote(idea_id: int, db: DB, user: CurrentUser):
    """Vote for an idea. Voting twice is a no-op: one vote per user per idea."""
    idea = await db.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "Idea not found")
    if await db.get(IdeaVote, (idea_id, user.id)) is None:
        db.add(IdeaVote(idea_id=idea_id, user_id=user.id))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
    return await _out(db, idea, user)


@router.delete("/{idea_id}/vote", response_model=IdeaOut)
async def unvote(idea_id: int, db: DB, user: CurrentUser):
    idea = await db.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "Idea not found")
    await db.execute(
        delete(IdeaVote).where(IdeaVote.idea_id == idea_id, IdeaVote.user_id == user.id)
    )
    await db.commit()
    return await _out(db, idea, user)


@router.delete("/{idea_id}", status_code=204)
async def delete_idea(idea_id: int, db: DB, user: CurrentUser):
    idea = await db.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "Idea not found")
    if idea.author_id != user.id and user.role not in ("admin", "organizer"):
        raise HTTPException(403, "Insufficient permissions")
    await db.delete(idea)
    await db.commit()

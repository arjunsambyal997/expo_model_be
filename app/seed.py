from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Idea, IdeaVote, User

DEMO_EMAIL = "demo@expo-summit.dev"
DEMO_PASSWORD = "demo12345"
ADMIN_EMAIL = "admin@expo-summit.dev"
ADMIN_PASSWORD = "admin12345"


async def seed() -> None:
    async with SessionLocal() as db:
        if (await db.scalar(select(User).limit(1))) is not None:
            return
        demo = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            name="Demo User",
            role="attendee",
            is_verified=True,
        )
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            name="Summit Admin",
            role="admin",
            is_verified=True,
        )
        db.add_all([demo, admin])
        await db.flush()
        idea = Idea(
            title="Example: AI concierge for first-time visitors",
            description=(
                "A sample idea to show how this works. Describe the problem, who it is for "
                "and what we would build, then let the team vote on it."
            ),
            author_id=demo.id,
        )
        db.add(idea)
        await db.flush()
        db.add(IdeaVote(idea_id=idea.id, user_id=demo.id))
        await db.commit()

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Speaker, Talk, User

SPEAKERS = [
    ("Layla Park", "Head of AI", "Nova Labs", True),
    ("Amir Khan", "CTO", "Gulf Data Co.", False),
    ("Maryam Saleh", "Director of AI Strategy", "Dubai Future Foundation", True),
    ("Daniel Reyes", "Research Scientist", "Atlas Research", False),
    ("Noor Al Mansoori", "Founder", "Sahara Robotics", True),
]

# (title, track, room, day, hour, minutes, speaker indexes)
TALKS = [
    ("Opening Keynote: The Future of Applied AI", "Keynote", "Hall A", 1, 9, 60, [2]),
    ("Agents in Production", "Panel", "Room 2", 1, 10, 60, [0, 1]),
    ("Hands-on: Building RAG Systems", "Workshop", "Room 4", 1, 12, 90, [3]),
    ("AI in Government Services", "Talk", "Hall B", 1, 14, 45, [2]),
    ("Robotics Beyond the Lab", "Talk", "Hall A", 2, 9, 45, [4]),
    ("Responsible AI at Scale", "Panel", "Room 2", 2, 11, 60, [0, 3]),
    ("Closing Keynote: AI and the Next Decade", "Keynote", "Hall A", 3, 16, 60, [4, 2]),
]


async def seed() -> None:
    async with SessionLocal() as db:
        if (await db.scalar(select(User).limit(1))) is not None:
            return
        db.add(
            User(
                email="admin@expo-summit.dev",
                password_hash=hash_password("admin12345"),
                name="Summit Admin",
                role="admin",
                is_verified=True,
            )
        )
        speakers = [
            Speaker(name=n, title=t, company=c, featured=f, bio=f"{n} leads work on practical AI.")
            for n, t, c, f in SPEAKERS
        ]
        db.add_all(speakers)
        base = datetime(2027, 3, 1, tzinfo=UTC)
        for title, track, room, day, hour, mins, sp in TALKS:
            start = base + timedelta(days=day - 1, hours=hour)
            db.add(
                Talk(
                    title=title,
                    track=track,
                    room=room,
                    day=day,
                    starts_at=start,
                    ends_at=start + timedelta(minutes=mins),
                    description="A session from the Dubai Expo AI Summit programme.",
                    speakers=[speakers[i] for i in sp],
                )
            )
        await db.commit()

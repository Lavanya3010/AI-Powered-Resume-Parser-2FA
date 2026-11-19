import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User


async def check_user():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        for user in users:
            print("User ID:", user.id)
            print("Name:", user.full_name)
            print("Email:", user.email)

    await engine_dispose()


async def engine_dispose():
    from app.database import engine
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_user())
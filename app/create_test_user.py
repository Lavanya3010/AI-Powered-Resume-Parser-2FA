
import asyncio

from app.database import AsyncSessionLocal
from app.models.user import User


async def create_user():
    async with AsyncSessionLocal() as db:
        user = User(
            full_name="Arun Kumar",
            email="arun.test@example.com",
            phone="9876543210",
            hashed_password="temporary_test_password"
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        print("Test user created successfully!")
        print("User ID:", user.id)

    await db.close()


if __name__ == "__main__":
    asyncio.run(create_user())

import asyncio
from sqlalchemy import inspect
from app.database import engine


async def verify():
    async with engine.connect() as connection:
        tables = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        print("Database tables:", tables)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
    
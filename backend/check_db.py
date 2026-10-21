import asyncio

from sqlalchemy import text

from app.core.database import SessionLocal

async def main():
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT 1")
        )

        print(result.scalar())


asyncio.run(main())
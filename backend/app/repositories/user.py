from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, 
        email: str,
        hashed_password: str,
    )->User:
        user = User(
            email=email,
            hashed_password= hashed_password,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user
    
    async def get_by_id(
        self,
        user_id: int
    )->User | None:
        statement = select(User).where(
            User.id == user_id
        )
        result = await self.db.execute(statement)

        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 20,
        offset: int = 0,
    )->list[User]:
        statement = select(User).order_by(User.id.desc()).limit(limit).offset(offset)

        result = await self.db.execute(statement)

        return list(result.scalars().all())
    
    async def get_by_email(
        self,
        email: str
    )->User | None:
        statement = select(User).where(User.email==email)

        result = await self.db.execute(statement)

        return result.scalar_one_or_none()
    

        

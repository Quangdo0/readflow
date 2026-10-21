from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    InvalidTokenError,
    decode_access_token,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.document import DocumentRepository
from app.services.document import DocumentService
from app.services.user import UserService


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    repository = UserRepository(db)
    return UserService(repository)


def get_document_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentService:
    repository = DocumentRepository(db)
    return DocumentService(repository)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError:
        raise credentials_exception

    repository = UserRepository(db)

    user = await repository.get_by_id(user_id)

    if user is None:
        raise credentials_exception

    return user
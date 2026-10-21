from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import get_user_service, get_current_user
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services.user import (
    EmailAlreadyExistsError,
    UserService,
)
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreate,
    service: UserService = Depends(
        get_user_service
    ),
):
    try:
        return await service.register(data)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
):
    try:
        token = await service.login(
            UserCreate(
                email=form_data.username,
                password=form_data.password,
            )
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
        )

    except InvalidCredentialError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model = UserRead
)
async def get_me(
    current_user: User = Depends(
        get_current_user
    )
):
    return current_user

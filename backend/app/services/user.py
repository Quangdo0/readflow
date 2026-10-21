from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token, InvalidTokenError
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)
class EmailAlreadyExistsError(Exception):
    pass

class InvalidCredentialError(Exception):
    pass

class UserService:
    def __init__(
        self,
        repository: UserRepository,
    ):
        self.repository = repository

    async def register(
        self,
        data: UserCreate,
    ) -> User:
        user_email = data.email
        user_password = data.password
        user = await self.repository.get_by_email(email = user_email)
        if user is not None:
            raise EmailAlreadyExistsError(
                "Email already exist"
            )
        return await self.repository.create(
            email = user_email,
            hashed_password = hash_password(user_password),
        )
    
    async def login(
        self,
        data: UserCreate
    )->str:
        user_email = data.email
        user_password = data.password
        user = await self.repository.get_by_email(email = user_email)
        if user is None:
            raise InvalidCredentialError(
                "Invalid email or password"
            )
        
        if not verify_password(plain_password = user_password, hashed_password = user.hashed_password):
            raise InvalidCredentialError(
                "Invalid email or password"
            )
        token = create_access_token(user_id = user.id)
        return token 
    
    async def get_current_user(
        self,
        token: str
    )->User:
        try:
            user_id = decode_access_token(token)

        except InvalidTokenError:
            raise InvalidCredentialError(
                "Invalid Credential"
            )


        



from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.db import get_db
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services.auth import AuthService
from app.services.redis import get_redis

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

signup_limiter = RateLimiter(times=10, seconds=60, key_prefix="auth:signup")
login_limiter = RateLimiter(times=10, seconds=60, key_prefix="auth:login")


def service(redis: Redis) -> AuthService:
    return AuthService(get_settings(), redis)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(signup_limiter)])
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)) -> TokenResponse:
    auth = service(redis)
    try:
        user = await auth.register(db, payload.email, payload.full_name, payload.password)
        token, expires_in = auth.create_token(user)
        await auth.store_session(token, user.id, expires_in)
        return TokenResponse(access_token=token, expires_in=expires_in, user=UserResponse.model_validate(user))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_limiter)])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)) -> TokenResponse:
    auth = service(redis)
    user = await auth.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token, expires_in = auth.create_token(user)
    await auth.store_session(token, user.id, expires_in)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    redis: Redis = Depends(get_redis),
) -> None:
    if credentials is None:
        return
    auth = service(redis)
    remaining = get_settings().access_token_minutes * 60
    await auth.revoke_session(credentials.credentials, remaining)

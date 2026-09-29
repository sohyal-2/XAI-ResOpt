from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import User

password_hash = PasswordHash.recommended()


class AuthService:
    def __init__(self, settings: Settings, redis: Redis):
        self.settings = settings
        self.redis = redis

    def hash_password(self, password: str) -> str:
        return password_hash.hash(password)

    def verify_password(self, password: str, stored_hash: str) -> bool:
        return password_hash.verify(password, stored_hash)

    def create_token(self, user: User) -> tuple[str, int]:
        expires_in = self.settings.access_token_minutes * 60
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.id),
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm), expires_in

    async def register(self, db: AsyncSession, email: str, full_name: str, password: str) -> User:
        normalized_email = email.strip().lower()
        existing = await db.scalar(select(User).where(User.email == normalized_email))
        if existing is not None:
            raise ValueError("An account with this email already exists.")
        user = User(email=normalized_email, full_name=full_name.strip(), password_hash=self.hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> User | None:
        user = await db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not user.is_active or not self.verify_password(password, user.password_hash):
            return None
        return user

    async def store_session(self, token: str, user_id: UUID, expires_in: int) -> None:
        payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        await self.redis.setex(f"auth:session:{payload['jti']}", expires_in, str(user_id))

    async def revoke_session(self, token: str, expires_in: int) -> None:
        payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        await self.redis.setex(f"auth:revoked:{payload['jti']}", max(expires_in, 1), "1")
        await self.redis.delete(f"auth:session:{payload['jti']}")

from dataclasses import dataclass

import asyncpg
from redis.asyncio import Redis


@dataclass(frozen=True)
class DependencyStatus:
    status: str
    detail: str | None = None


async def check_database(database_url: str) -> DependencyStatus:
    connection: asyncpg.Connection | None = None
    try:
        connection = await asyncpg.connect(database_url, timeout=2)
        await connection.execute("SELECT 1")
        return DependencyStatus(status="ok")
    except Exception as error:
        return DependencyStatus(status="error", detail=str(error))
    finally:
        if connection is not None:
            await connection.close()


async def check_redis(redis_url: str) -> DependencyStatus:
    client = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
    try:
        response = await client.ping()
        return DependencyStatus(status="ok" if response else "error")
    except Exception as error:
        return DependencyStatus(status="error", detail=str(error))
    finally:
        await client.aclose()
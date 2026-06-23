import ssl as _ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _build_engine():
    url = settings.database_url

    # Ensure async driver: convert postgresql:// → postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    # Strip sslmode from URL query params — asyncpg doesn't support it as a query param
    if "sslmode=" in url:
        import re
        url = re.sub(r"[?&]sslmode=[^&]*", "", url)
        # Clean up leftover ? or & at end
        url = url.rstrip("?&")

    kwargs: dict = {"echo": settings.app_env == "development"}

    if url.startswith("postgresql"):
        # PostgreSQL (Neon, etc.) — connection pool + SSL
        kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True})
        # asyncpg needs an SSLContext, not a string
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
        kwargs["connect_args"] = {"ssl": ssl_ctx}

    return create_async_engine(url, **kwargs)


engine = _build_engine()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

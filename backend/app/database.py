import ssl as _ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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

    # Strip sslmode from URL — asyncpg does not accept it as a query param
    if "sslmode" in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        params.pop("sslmode", None)
        url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

    kwargs: dict = {"echo": settings.app_env == "development"}

    if "postgresql" in url:
        # PostgreSQL (Neon, etc.) — connection pool + SSL
        kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True})
        # asyncpg needs a proper SSLContext object
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

        # Widen columns that were too narrow in initial schema
        if "postgresql" in str(engine.url):
            from sqlalchemy import text
            await conn.execute(text(
                "ALTER TABLE facility_matches ALTER COLUMN status TYPE VARCHAR(30)"
            ))

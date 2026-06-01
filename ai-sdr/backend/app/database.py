import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.config import get_settings

settings = get_settings()


def get_engine():
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif settings.DATABASE_URL.startswith("postgresql"):
        connect_args = {}
    return create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, connect_args=connect_args)


engine = get_engine()
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Log which DB is in use (password redacted)
import logging
_log = logging.getLogger(__name__)
_db_url_log = settings.DATABASE_URL
if "@" in _db_url_log:
    _db_url_log = _db_url_log.split("@")[0].split("://")[0] + "://****:****@" + _db_url_log.split("@")[1]
_log.info("=== DATABASE_URL in use: %s ===", _db_url_log)
_log.info("=== RAILWAY_SERVICE_ID=%s ===", os.environ.get("RAILWAY_SERVICE_ID", "(not set)"))


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> bool:
    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)
        return True
    else:
        try:
            async with engine.begin() as conn:
                tables = sorted(Base.metadata.tables.keys())
                _log.info("=== Tables registered in Base.metadata (%d): %s ===", len(tables), tables)

                await conn.run_sync(Base.metadata.create_all)

                from sqlalchemy import text
                result = await conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                )
                created = sorted(row[0] for row in result.fetchall())
                _log.info("=== Tables found in PostgreSQL (%d): %s ===", len(created), created)
                missing = set(Base.metadata.tables.keys()) - set(created)
                # Also check feature_flags specifically — if missing, fallback to raw SQL
                has_feature_flags = "feature_flags" in created
                if not has_feature_flags:
                    _log.warning("=== feature_flags table missing — running railway_schema.sql fallback ===")
                    import pathlib
                    schema_path = pathlib.Path(__file__).resolve().parent.parent / "railway_schema.sql"
                    if schema_path.exists():
                        raw_sql = schema_path.read_text()
                        for statement in raw_sql.split(";"):
                            stmt = statement.strip()
                            if stmt:
                                try:
                                    await conn.execute(text(stmt + ";"))
                                except Exception as se:
                                    _log.warning("SQL fallback statement skipped (likely already exists): %.100s", str(se))
                        _log.info("=== railway_schema.sql fallback executed ===")
                        has_feature_flags = True
                    else:
                        _log.warning("=== railway_schema.sql not found at %s ===", schema_path)

                if missing and has_feature_flags:
                    _log.warning("=== Tables MISSING after create_all (will be ignored): %s ===", sorted(missing))

                try:
                    await conn.execute(
                        text("ALTER TABLE email_messages ADD COLUMN direction VARCHAR(20) DEFAULT 'outbound'")
                    )
                except Exception:
                    pass
            return True
        except Exception as e:
            import traceback
            _log.critical("=== FAILED to connect to PostgreSQL: %s ===", e)
            _log.critical(traceback.format_exc())
            return False


SUPABASE_URL: Optional[str] = None
SUPABASE_SERVICE_KEY: Optional[str] = None
SUPABASE_ANON_KEY: Optional[str] = None


def init_supabase():
    global SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
    SUPABASE_URL = settings.SUPABASE_URL
    SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY
    SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY

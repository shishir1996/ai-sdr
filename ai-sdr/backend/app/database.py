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
_log.warning("=== DATABASE_URL in use: %s ===", _db_url_log)
_log.warning("=== RAILWAY_SERVICE_ID=%s ===", os.environ.get("RAILWAY_SERVICE_ID", "(not set)"))


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
                _log.warning("=== Tables registered in Base.metadata (%d): %s ===", len(tables), tables)

                await conn.run_sync(Base.metadata.create_all)

                from sqlalchemy import text
                result = await conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                )
                created = sorted(row[0] for row in result.fetchall())
                _log.warning("=== Tables found in PostgreSQL (%d): %s ===", len(created), created)
                missing = set(Base.metadata.tables.keys()) - set(created)
                # Also check feature_flags specifically — if missing, fallback to raw SQL
                has_feature_flags = "feature_flags" in created
                if not has_feature_flags:
                    _log.warning("=== feature_flags table missing — running railway_schema.sql fallback ===")
                    import pathlib
                    # Try multiple paths for railway_schema.sql
                    schema_candidates = [
                        pathlib.Path(__file__).resolve().parent.parent / "railway_schema.sql",
                        pathlib.Path.cwd() / "railway_schema.sql",
                        pathlib.Path("/app/railway_schema.sql"),
                        pathlib.Path("/railway_schema.sql"),
                    ]
                    raw_sql = None
                    for p in schema_candidates:
                        if p.exists():
                            raw_sql = p.read_text()
                            _log.warning("=== Found railway_schema.sql at %s ===", p)
                            break
                    if raw_sql:
                        for statement in raw_sql.split(";"):
                            stmt = statement.strip()
                            if stmt and not stmt.startswith("--"):
                                try:
                                    await conn.execute(text(stmt + ";"))
                                except Exception as se:
                                    _log.warning("SQL fallback statement skipped: %.100s", str(se))
                        # Re-verify table was actually created
                        result2 = await conn.execute(
                            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                        )
                        created2 = sorted(row[0] for row in result2.fetchall())
                        has_feature_flags = "feature_flags" in created2
                        if has_feature_flags:
                            _log.warning("=== railway_schema.sql fallback SUCCEEDED — feature_flags created ===")
                            created = created2
                        else:
                            _log.warning("=== railway_schema.sql fallback FAILED — feature_flags still missing ===")
                    else:
                        _log.warning("=== railway_schema.sql not found (tried %d paths) ===", len(schema_candidates))

                if missing and has_feature_flags:
                    _log.warning("=== Tables MISSING after create_all (will be ignored): %s ===", sorted(missing))

                # Use SAVEPOINT so ALTER TABLE failure doesn't abort the entire transaction
                try:
                    await conn.execute(text("SAVEPOINT alter_savepoint"))
                    await conn.execute(
                        text("ALTER TABLE email_messages ADD COLUMN direction VARCHAR(20) DEFAULT 'outbound'")
                    )
                    await conn.execute(text("RELEASE SAVEPOINT alter_savepoint"))
                except Exception:
                    try:
                        await conn.execute(text("ROLLBACK TO SAVEPOINT alter_savepoint"))
                    except Exception:
                        pass

                for col in [
                    "ADD COLUMN business_type VARCHAR(255)",
                    "ADD COLUMN city VARCHAR(255)",
                    "ADD COLUMN state VARCHAR(255)",
                    "ADD COLUMN country VARCHAR(100)",
                    "ADD COLUMN postal_code VARCHAR(20)",
                ]:
                    try:
                        await conn.execute(text("SAVEPOINT mig_sp"))
                        await conn.execute(text(f"ALTER TABLE research_results {col}"))
                        await conn.execute(text("RELEASE SAVEPOINT mig_sp"))
                    except Exception:
                        try:
                            await conn.execute(text("ROLLBACK TO SAVEPOINT mig_sp"))
                        except Exception:
                            pass

            for tname, cols in [
                ("missions", [
                    "ADD COLUMN org_id VARCHAR",
                    "ADD COLUMN vp_id VARCHAR",
                    "ADD COLUMN name VARCHAR(255)",
                    "ADD COLUMN objective TEXT",
                    "ADD COLUMN kpi_target TEXT",
                    "ADD COLUMN status VARCHAR(50) DEFAULT 'draft'",
                    "ADD COLUMN vp_reasoning TEXT",
                ]),
                ("mission_tasks", [
                    "ADD COLUMN mission_id VARCHAR",
                    "ADD COLUMN org_id VARCHAR",
                    "ADD COLUMN agent_type VARCHAR(50)",
                    "ADD COLUMN agent_id VARCHAR",
                    "ADD COLUMN objective TEXT",
                    "ADD COLUMN execution_plan JSON",
                    "ADD COLUMN status VARCHAR(50) DEFAULT 'pending'",
                    "ADD COLUMN report JSON",
                    "ADD COLUMN confidence_score FLOAT",
                    "ADD COLUMN vp_feedback VARCHAR(50)",
                    "ADD COLUMN vp_notes TEXT",
                ]),
                ("agent_memories", [
                    "ADD COLUMN org_id VARCHAR",
                    "ADD COLUMN agent_type VARCHAR(50)",
                    "ADD COLUMN memory_type VARCHAR(50)",
                    "ADD COLUMN content JSON",
                ]),
                ("agent_performance", [
                    "ADD COLUMN org_id VARCHAR",
                    "ADD COLUMN agent_type VARCHAR(50)",
                    "ADD COLUMN metric_name VARCHAR(100)",
                    "ADD COLUMN metric_value FLOAT DEFAULT 0",
                    "ADD COLUMN period VARCHAR(50) DEFAULT 'all_time'",
                ]),
            ]:
                for col in cols:
                    try:
                        await conn.execute(text("SAVEPOINT mig_vp"))
                        await conn.execute(text(f"ALTER TABLE {tname} {col}"))
                        await conn.execute(text("RELEASE SAVEPOINT mig_vp"))
                    except Exception:
                        try:
                            await conn.execute(text("ROLLBACK TO SAVEPOINT mig_vp"))
                        except Exception:
                            pass

            for col in [
                "ADD COLUMN outreach_active BOOLEAN DEFAULT FALSE",
                "ADD COLUMN target_titles TEXT",
                "ADD COLUMN target_business_types TEXT",
            ]:
                    try:
                        await conn.execute(text("SAVEPOINT mig_sp2"))
                        await conn.execute(text(f"ALTER TABLE vp_sales_profiles {col}"))
                        await conn.execute(text("RELEASE SAVEPOINT mig_sp2"))
                    except Exception:
                        try:
                            await conn.execute(text("ROLLBACK TO SAVEPOINT mig_sp2"))
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

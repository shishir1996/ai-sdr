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

                # Single helper: query information_schema first, only ALTER if column missing.
                # This avoids the SAVEPOINT/asyncpg interaction problem.
                async def _add_columns_if_missing(table: str, column_defs: list) -> None:
                    """Add columns to `table` if they don't exist. column_defs is a list of dicts: {name, type, default, nullable}."""
                    for cd in column_defs:
                        col_name = cd["name"]
                        try:
                            exists = await conn.execute(
                                text(
                                    "SELECT 1 FROM information_schema.columns "
                                    "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
                                ),
                                {"t": table, "c": col_name},
                            )
                            if exists.first() is not None:
                                continue
                            nullable = "NULL" if cd.get("nullable", True) else "NOT NULL"
                            default = f" DEFAULT {cd['default']}" if cd.get("default") is not None else ""
                            sql = f'ALTER TABLE "{table}" ADD COLUMN "{col_name}" {cd["type"]} {nullable}{default}'
                            await conn.execute(text(sql))
                            _log.warning("=== Added column %s.%s ===", table, col_name)
                        except Exception as ce:
                            _log.warning("=== _add_columns_if_missing skipped %s.%s: %s ===", table, col_name, ce)

                await _add_columns_if_missing("email_messages", [
                    {"name": "direction", "type": "VARCHAR(20)", "nullable": True, "default": "'outbound'"},
                ])

                # Apply all migrations (each column is queried first, only added if missing).
                # NOTE: this is the actual source of truth for the live DB schema. When adding
                # new columns to a model, ALSO add them here.
                await _add_columns_if_missing(conn, "research_results", [
                    {"name": "business_type", "type": "VARCHAR(255)", "nullable": True},
                    {"name": "city", "type": "VARCHAR(255)", "nullable": True},
                    {"name": "state", "type": "VARCHAR(255)", "nullable": True},
                    {"name": "country", "type": "VARCHAR(100)", "nullable": True},
                    {"name": "postal_code", "type": "VARCHAR(20)", "nullable": True},
                ])

                await _add_columns_if_missing(conn, "missions", [
                    {"name": "org_id", "type": "VARCHAR", "nullable": True},
                    {"name": "vp_id", "type": "VARCHAR", "nullable": True},
                    {"name": "name", "type": "VARCHAR(255)", "nullable": True},
                    {"name": "objective", "type": "TEXT", "nullable": True},
                    {"name": "kpi_target", "type": "TEXT", "nullable": True},
                    {"name": "status", "type": "VARCHAR(50)", "nullable": True, "default": "'draft'"},
                    {"name": "vp_reasoning", "type": "TEXT", "nullable": True},
                ])

                await _add_columns_if_missing(conn, "mission_tasks", [
                    {"name": "mission_id", "type": "VARCHAR", "nullable": True},
                    {"name": "org_id", "type": "VARCHAR", "nullable": True},
                    {"name": "agent_type", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "agent_id", "type": "VARCHAR", "nullable": True},
                    {"name": "objective", "type": "TEXT", "nullable": True},
                    {"name": "execution_plan", "type": "JSON", "nullable": True},
                    {"name": "status", "type": "VARCHAR(50)", "nullable": True, "default": "'pending'"},
                    {"name": "report", "type": "JSON", "nullable": True},
                    {"name": "confidence_score", "type": "FLOAT", "nullable": True},
                    {"name": "vp_feedback", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "vp_notes", "type": "TEXT", "nullable": True},
                ])

                await _add_columns_if_missing(conn, "agent_memories", [
                    {"name": "org_id", "type": "VARCHAR", "nullable": True},
                    {"name": "agent_type", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "memory_type", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "content", "type": "JSON", "nullable": True},
                ])

                await _add_columns_if_missing(conn, "agent_performance", [
                    {"name": "org_id", "type": "VARCHAR", "nullable": True},
                    {"name": "agent_type", "type": "VARCHAR(50)", "nullable": True},
                    {"name": "metric_name", "type": "VARCHAR(100)", "nullable": True},
                    {"name": "metric_value", "type": "FLOAT", "nullable": True, "default": "0"},
                    {"name": "period", "type": "VARCHAR(50)", "nullable": True, "default": "'all_time'"},
                ])

                # === SDR profile channel + Vapi credentials ===
                await _add_columns_if_missing(conn, "sdr_profiles", [
                    {"name": "vapi_credentials_encrypted", "type": "TEXT", "nullable": True},
                    {"name": "email_enabled", "type": "BOOLEAN", "nullable": True, "default": "TRUE"},
                    {"name": "linkedin_enabled", "type": "BOOLEAN", "nullable": True, "default": "TRUE"},
                    {"name": "vapi_enabled", "type": "BOOLEAN", "nullable": True, "default": "FALSE"},
                ])

                # === VP sales profile: outreach toggle + data source selection ===
                await _add_columns_if_missing(conn, "vp_sales_profiles", [
                    {"name": "outreach_active", "type": "BOOLEAN", "nullable": True, "default": "FALSE"},
                    {"name": "target_titles", "type": "TEXT", "nullable": True},
                    {"name": "target_business_types", "type": "TEXT", "nullable": True},
                    {"name": "data_source", "type": "VARCHAR(50)", "nullable": True, "default": "'web_scraping'"},
                    {"name": "data_source_config", "type": "JSON", "nullable": True},
                    {"name": "manual_upload_done", "type": "BOOLEAN", "nullable": True, "default": "FALSE"},
                ])

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

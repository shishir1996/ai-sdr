import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vp_sales import ResearchAgent, ResearchResult, VPActionLog
from app.services.research.search_service import search_all_enabled
from app.services.lead_sources.service import get_enabled_sources

logger = logging.getLogger(__name__)


async def create_research_agent(
    db: AsyncSession,
    org_id: str,
    vp_id: Optional[str],
    name: str,
    search_queries: Optional[str] = None,
    target_industry: Optional[str] = None,
    target_country: Optional[str] = None,
    target_audience: Optional[str] = None,
    max_leads: int = 50,
) -> ResearchAgent:
    sources = await get_enabled_sources(db, org_id)
    agent = ResearchAgent(
        org_id=org_id,
        vp_id=vp_id,
        name=name,
        search_queries=search_queries,
        target_industry=target_industry,
        target_country=target_country,
        target_audience=target_audience,
        max_leads=max_leads,
        status="idle",
        enabled_sources=sources,
    )
    db.add(agent)
    await db.flush()
    return agent


async def execute_research(db: AsyncSession, agent_id: str) -> int:
    result = await db.execute(select(ResearchAgent).where(ResearchAgent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return 0

    if agent.status == "running":
        return 0

    agent.status = "running"
    agent.last_run_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.flush()

    queries = (agent.search_queries or "").split("\n")
    queries = [q.strip() for q in queries if q.strip()]

    if not queries and agent.target_industry:
        queries = [
            f"{agent.target_audience or ''} companies in {agent.target_country or ''} {agent.target_industry}"
        ]

    total = 0
    for query in queries[:5]:
        try:
            results = await search_all_enabled(db, agent.org_id, query, num_results=10)
            for r in results:
                research_result = ResearchResult(
                    org_id=agent.org_id,
                    research_agent_id=agent.id,
                    source=r.get("_source", "web_research"),
                    source_url=r.get("link", ""),
                    title=r.get("title", ""),
                    snippet=r.get("snippet", ""),
                    company_name=r.get("company_name", ""),
                    contact_name=r.get("contact_name", ""),
                    contact_title=r.get("contact_title", ""),
                    contact_email=r.get("contact_email", ""),
                    contact_phone=r.get("contact_phone", ""),
                    website=r.get("website", ""),
                    industry=r.get("industry", agent.target_industry or ""),
                    business_type=r.get("business_type", ""),
                    location=r.get("location", agent.target_country or ""),
                    city=r.get("city", ""),
                    state=r.get("state", ""),
                    country=r.get("country", ""),
                    postal_code=r.get("postal_code", ""),
                    raw_data=r,
                    status="new",
                )
                db.add(research_result)
                total += 1
        except Exception as e:
            logger.warning("Research query failed '%s': %s", query, e)

    agent.leads_discovered = (agent.leads_discovered or 0) + total
    agent.status = "completed"
    await db.flush()

    vp_log = VPActionLog(
        org_id=agent.org_id,
        vp_id=agent.vp_id,
        action_type="research_completed",
        reasoning=f"Research agent '{agent.name}' discovered {total} leads across {len(queries)} queries",
        details={
            "agent_id": agent.id,
            "agent_name": agent.name,
            "queries": queries,
            "leads_found": total,
            "sources_used": agent.enabled_sources,
        },
    )
    db.add(vp_log)
    await db.flush()

    return total


async def convert_to_lead(
    db: AsyncSession,
    org_id: str,
    result_id: str,
) -> Optional[str]:
    from app.models.lead import Lead
    result_row = await db.execute(select(ResearchResult).where(ResearchResult.id == result_id))
    result = result_row.scalar_one_or_none()
    if not result or result.converted_to_lead:
        return None

    first_name, last_name = "", ""
    if result.contact_name:
        name_parts = result.contact_name.strip().split(None, 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

    lead = Lead(
        org_id=org_id,
        first_name=first_name or None,
        last_name=last_name or None,
        company=result.company_name,
        email=result.contact_email,
        phone=result.contact_phone,
        title=result.contact_title,
        industry=result.industry or result.business_type,
        location=result.location,
        city=result.city,
        state=result.state,
        country=result.country,
        postal_code=result.postal_code,
        website=result.website,
        source=f"research_{result.source}",
        status="new",
    )
    db.add(lead)
    await db.flush()

    result.lead_id = lead.id
    result.converted_to_lead = True
    await db.flush()

    return lead.id


async def get_agent_results(
    db: AsyncSession,
    agent_id: str,
    limit: int = 50,
) -> list[ResearchResult]:
    result = await db.execute(
        select(ResearchResult)
        .where(ResearchResult.research_agent_id == agent_id)
        .order_by(ResearchResult.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

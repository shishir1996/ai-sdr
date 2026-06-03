import logging
import json
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.models.lead_intelligence import BuyingSignal
from app.services.research.search_service import search_news_sites, search_web_general, _scrape_html, _extract_text
from app.services.ai.provider import generate_text

logger = logging.getLogger(__name__)

SIGNAL_KEYWORDS = {
    "hiring": ["hiring", "job opening", "careers", "we're hiring", "recruiting"],
    "funding": ["raised", "funding", "series a", "series b", "venture capital", "investment"],
    "expansion": ["expanding", "new office", "opening", "expansion", "growing team"],
    "acquisition": ["acquired", "acquisition", "merger", "buying"],
    "partnership": ["partnership", "partner", "collaboration", "strategic alliance"],
    "product_launch": ["launch", "new product", "announcing", "introducing"],
    "technology": ["migrating to", "moving to", "implementing", "deploying", "adopting"],
}


class BuyingSignalAgent(BaseAgent):
    """Detects sales opportunities by monitoring company activities.

    Monitors: hiring, funding, expansion, acquisitions, partnerships,
    product launches, technology migrations.
    """

    agent_type = "buying_signal"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Detecting buying signals")
        steps = plan.get("steps", [{"name": "detect_signals", "description": "Detect buying signals"}])
        all_signals = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_signals.extend(step_result.get("signals", []))
            recommendations.extend(step_result.get("recommendations", []))

        top_signals = [s for s in all_signals if s.get("signal_strength", 0) >= 0.6]
        intent_score = min(1.0, (len(top_signals) * 0.25) + 0.1)

        return {
            "work_completed": f"Detected {len(all_signals)} buying signals ({len(top_signals)} strong)",
            "findings": all_signals,
            "confidence": intent_score,
            "risks": ["News sources may not cover all companies"],
            "recommendations": recommendations or [
                "Prioritize leads with strong buying signals",
                "Set up Google Alerts for high-value targets",
            ],
            "next_action": "score_lead" if all_signals else "monitor_for_signals",
        }

    async def _execute_step(self, step: dict) -> dict:
        company = step.get("company", step.get("description", ""))
        signals = []

        for signal_type, keywords in SIGNAL_KEYWORDS.items():
            try:
                for kw in keywords[:2]:
                    query = f"{company} {kw}"
                    results = await search_news_sites(query, num_results=3)
                    for r in results:
                        if r.get("link"):
                            html = await _scrape_html(r["link"])
                            snippet = _extract_text(html)[:500] if html else r.get("snippet", "")

                            strength = 0.5
                            if signal_type in ("funding", "acquisition"):
                                strength = 0.9
                            elif signal_type in ("expansion", "hiring"):
                                strength = 0.7

                            signals.append({
                                "signal_type": signal_type,
                                "signal_description": r.get("title", ""),
                                "signal_source": signal_type,
                                "signal_url": r.get("link", ""),
                                "signal_strength": strength,
                                "intent_score": strength * 0.8,
                                "company": company,
                                "snippet": snippet[:300],
                            })

                    if signals:
                        break
            except Exception as e:
                logger.warning("Signal detection failed for %s: %s", signal_type, e)

        if not signals:
            signals.append({
                "signal_type": "no_signals_detected",
                "signal_description": f"No recent buying signals found for {company}",
                "signal_source": "monitoring",
                "signal_strength": 0.1,
                "intent_score": 0.1,
                "company": company,
            })

        return {"signals": signals, "recommendations": ["Check company news weekly for signal updates"]}

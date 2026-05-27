import asyncio
import dns.asyncresolver
from typing import Optional


async def resolve_txt(domain: str) -> list[str]:
    try:
        answers = await dns.asyncresolver.resolve(domain, "TXT", lifetime=10)
        return [txt.to_text().strip('"') for rdata in answers for txt in rdata.strings]
    except Exception:
        return []


async def resolve_mx(domain: str) -> list[dict]:
    try:
        answers = await dns.asyncresolver.resolve(domain, "MX", lifetime=10)
        return [
            {"host": str(rdata.exchange).rstrip("."), "priority": rdata.preference}
            for rdata in answers
        ]
    except Exception:
        return []


async def resolve_cname(domain: str) -> Optional[str]:
    try:
        answers = await dns.asyncresolver.resolve(domain, "CNAME", lifetime=10)
        return str(answers[0].target).rstrip(".")
    except Exception:
        return None


async def check_spf(domain: str) -> dict:
    records = await resolve_txt(domain)
    spf_records = [r for r in records if r.startswith("v=spf1")]
    return {
        "found": len(spf_records) > 0,
        "records": spf_records,
        "raw": records,
    }


async def check_dkim(domain: str, selector: str = "default") -> dict:
    dkim_domain = f"{selector}._domainkey.{domain}"
    records = await resolve_txt(dkim_domain)
    return {
        "found": len(records) > 0,
        "selector": selector,
        "records": records,
    }


async def check_dmarc(domain: str) -> dict:
    dmarc_domain = f"_dmarc.{domain}"
    records = await resolve_txt(dmarc_domain)
    dmarc_records = [r for r in records if r.startswith("v=DMARC1")]
    return {
        "found": len(dmarc_records) > 0,
        "records": dmarc_records,
        "raw": records,
    }


async def check_mx(domain: str) -> dict:
    records = await resolve_mx(domain)
    return {
        "found": len(records) > 0,
        "records": records,
    }


async def check_all(domain: str, dkim_selector: str = "default") -> dict:
    spf_result, dkim_result, dmarc_result, mx_result = await asyncio.gather(
        check_spf(domain),
        check_dkim(domain, dkim_selector),
        check_dmarc(domain),
        check_mx(domain),
    )
    return {
        "domain": domain,
        "spf": spf_result,
        "dkim": dkim_result,
        "dmarc": dmarc_result,
        "mx": mx_result,
        "all_configured": all([
            spf_result["found"],
            dmarc_result["found"],
            mx_result["found"],
        ]),
    }

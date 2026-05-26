import time
from collections import defaultdict
from typing import Optional


class RateLimiter:
    def __init__(self):
        self._email_counts: dict[str, list[float]] = defaultdict(list)
        self._call_counts: dict[str, list[float]] = defaultdict(list)
        self._linkedin_counts: dict[str, list[float]] = defaultdict(list)

    def _prune(self, counts: list[float], window: float):
        now = time.time()
        while counts and counts[0] < now - window:
            counts.pop(0)

    def check_email(self, org_id: str, max_per_day: int = 20) -> tuple[bool, int]:
        self._prune(self._email_counts[org_id], 86400)
        self._email_counts[org_id].append(time.time())
        remaining = max_per_day - len(self._email_counts[org_id])
        return (len(self._email_counts[org_id]) <= max_per_day), max(0, remaining)

    def check_call(self, org_id: str, max_per_day: int = 10) -> tuple[bool, int]:
        self._prune(self._call_counts[org_id], 86400)
        self._call_counts[org_id].append(time.time())
        remaining = max_per_day - len(self._call_counts[org_id])
        return (len(self._call_counts[org_id]) <= max_per_day), max(0, remaining)

    def check_linkedin(self, org_id: str, max_per_day: int = 15) -> tuple[bool, int]:
        self._prune(self._linkedin_counts[org_id], 86400)
        self._linkedin_counts[org_id].append(time.time())
        remaining = max_per_day - len(self._linkedin_counts[org_id])
        return (len(self._linkedin_counts[org_id]) <= max_per_day), max(0, remaining)

    def get_usage(self, org_id: str) -> dict:
        self._prune(self._email_counts[org_id], 86400)
        self._prune(self._call_counts[org_id], 86400)
        self._prune(self._linkedin_counts[org_id], 86400)
        return {
            "emails_today": len(self._email_counts.get(org_id, [])),
            "calls_today": len(self._call_counts.get(org_id, [])),
            "linkedin_today": len(self._linkedin_counts.get(org_id, [])),
        }

    def reset_org(self, org_id: str):
        self._email_counts.pop(org_id, None)
        self._call_counts.pop(org_id, None)
        self._linkedin_counts.pop(org_id, None)


rate_limiter = RateLimiter()

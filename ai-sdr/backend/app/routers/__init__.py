from fastapi import APIRouter
from app.database import engine

router = APIRouter()


@router.get("/health")
async def health_check():
    url = str(engine.url)
    if "@" in url:
        url = url.split("@")[0].split("://")[0] + "://****:****@" + url.split("@")[1][:30] + "..."
    return {"status": "ok", "service": "ai-sdr", "database": url}

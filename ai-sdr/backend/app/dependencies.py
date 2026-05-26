from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.feature_flag.service import is_feature_enabled


async def require_feature(feature_key: str):
    async def _check(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        enabled = await is_feature_enabled(db, feature_key, user.org_id)
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_key}' is disabled",
            )
        return user
    return _check

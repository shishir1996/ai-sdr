import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models.user import User, Organization
from app.utils.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, get_current_user
from app.config import get_settings
from app.services.auth.supabase_auth import (
    supabase_signup, supabase_send_password_reset,
    supabase_reset_password, supabase_get_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    org_name: str
    phone: Optional[str] = None
    country_code: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    email_verified: bool = True


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None


@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org = Organization(name=req.org_name, slug=req.org_name.lower().replace(" ", "-"))
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
        role="admin",
    )
    # Store optional fields if the columns exist (post-migration)
    for attr, val in [("phone", req.phone), ("country_code", req.country_code)]:
        if val is not None:
            try:
                setattr(user, attr, val)
            except Exception:
                pass
    db.add(user)
    await db.flush()

    # Create user in Supabase Auth (sends verification email)
    try:
        redirect_url = f"{settings.FRONTEND_URL}/login?verified=true"
        supabase_result = await supabase_signup(req.email, req.password, redirect_to=redirect_url)
        supabase_user = supabase_result.get("user") or supabase_result.get("id", {})
        if supabase_user:
            supabase_uid = supabase_user.get("id")
            if supabase_uid:
                try:
                    setattr(user, "supabase_uid", supabase_uid)
                    setattr(user, "email_verified", False)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Supabase signup failed (proceeding with local auth): {e}")

    access_token = create_access_token({"sub": user.id, "org_id": org.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})
    email_verified = getattr(user, "email_verified", True)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, email_verified=email_verified)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        email_verified=getattr(user, "email_verified", True),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "org_id": user.org_id,
        "phone": getattr(user, "phone", None),
        "country_code": getattr(user, "country_code", None),
        "email_verified": getattr(user, "email_verified", True),
    }


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    redirect_url = f"{settings.FRONTEND_URL}/reset-password"
    try:
        await supabase_send_password_reset(req.email, redirect_to=redirect_url)
        return {"message": "Password reset email sent. Check your inbox."}
    except Exception as e:
        logger.warning(f"Failed to send password reset email: {e}")
        # Don't reveal if email exists or not for security
        return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    # Verify the Supabase access token is valid
    try:
        supabase_user_data = await supabase_get_user(req.access_token)
        supabase_email = supabase_user_data.get("email") or supabase_user_data.get("id")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired reset token")

    # Find the local user
    result = await db.execute(select(User).where(User.email == supabase_email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update password in Supabase
    try:
        await supabase_reset_password(req.access_token, req.new_password)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to reset password: {e}")

    # Update local password hash
    user.password_hash = hash_password(req.new_password)
    await db.flush()

    return {"message": "Password reset successful. You can now sign in with your new password."}


@router.put("/profile")
async def update_profile(
    req: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.name is not None:
        current_user.name = req.name
    if req.phone is not None:
        try:
            current_user.phone = req.phone
        except Exception:
            pass
    if req.country_code is not None:
        try:
            current_user.country_code = req.country_code
        except Exception:
            pass
    await db.flush()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "phone": getattr(current_user, "phone", None),
        "country_code": getattr(current_user, "country_code", None),
    }




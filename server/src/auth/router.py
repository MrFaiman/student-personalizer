from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session, select

from ..database import get_session
from .dependencies import get_current_user, require_admin, require_viewer
from .models import User, UserRole
from .schemas import (
    AdminResetPasswordRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from .service import AuthService
from .tokens import decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, session: Session = Depends(get_session)):
    return AuthService(session).login(body, request)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
):
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            AuthService(session).logout(payload.get("jti", ""))
        except JWTError:
            pass  # Already invalid, still return 200
    return {"ok": True}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: Session = Depends(get_session)):
    return AuthService(session).refresh(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.put("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    AuthService(session).change_password(user, body)
    return {"ok": True}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return session.exec(select(User)).all()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return AuthService(session).create_user(body)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from uuid import UUID
    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from uuid import UUID
    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    AuthService(session).admin_reset_password(user, body.new_password, body.must_change_password)
    return {"ok": True}

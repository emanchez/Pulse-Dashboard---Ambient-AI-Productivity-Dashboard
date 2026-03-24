from fastapi import APIRouter, HTTPException, Request, Response, status, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.limiter import limiter
from ..core.security import create_access_token, decode_access_token, verify_password
from ..db.session import get_async_session
from ..models.user import User, UserSchema

router = APIRouter()

_settings = get_settings()
# In prod, limit login attempts to 5/min; dev uses 100/min to allow fast test suites.
_LOGIN_RATE_LIMIT = "5/minute" if _settings.app_env == "prod" else "100/minute"


class LoginRequest(BaseModel):
    username: str
    password: str


async def _log_auth_event(
    action_type: str,
    change_summary: str,
    user_id: str | None,
    client_host: str | None,
) -> None:
    """Write an auth event to action_logs. Never raises — errors are swallowed."""
    # Lazy imports break the circular dependency:
    #   auth.py → models.action_log → schemas.base → schemas/__init__.py → models.action_log
    from ..db.session import async_session  # noqa: PLC0415
    from ..models.action_log import ActionLog  # noqa: PLC0415

    try:
        async with async_session() as session:
            log = ActionLog(
                action_type=action_type,
                change_summary=change_summary,
                user_id=user_id,
                client_host=client_host,
            )
            session.add(log)
            await session.commit()
    except Exception:
        pass  # Auth logging must never block or break the login response


@router.post("/login")
@limiter.limit(_LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    q = await session.execute(select(User).filter_by(username=payload.username))
    user: User | None = q.scalars().first()
    client_host = request.client.host if request.client else None

    if not user or not verify_password(payload.password, user.hashed_password):
        await _log_auth_event(
            action_type="LOGIN_FAILED",
            change_summary=f"Failed login attempt for username '{payload.username}'",
            user_id=None,
            client_host=client_host,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await _log_auth_event(
        action_type="LOGIN_SUCCESS",
        change_summary=f"Successful login for user '{user.username}'",
        user_id=str(user.id),
        client_host=client_host,
    )
    token = create_access_token(subject=str(user.id))
    cookie_max_age = _settings.access_token_expire_minutes * 60

    # Set the httpOnly JWT cookie in all environments so this logic is covered by tests.
    # In production the JWT is not exposed in the response body; in dev it is, to
    # preserve existing tooling and test expectations.
    #
    # SameSite: production uses "none" because the frontend (Vercel) and backend
    # (Railway) are on different domains — SameSite=Lax blocks cross-origin fetch
    # calls, so the cookie is never sent after login.  SameSite=None requires
    # Secure=True (already enforced; Railway uses HTTPS).  Dev uses "lax" since
    # localhost is same-site and SameSite=None is rejected over plain HTTP anyway.
    #
    # Note: csrf_token cookie removed (Phase 4.2 CSRF fix).  CSRF is now enforced
    # via custom-header presence (X-CSRF-Token: any-non-empty-value).  The old
    # double-submit cookie pattern broke in production because the frontend (Vercel)
    # and backend (Railway) are on different domains — browser SOP prevents JS from
    # reading cookies set by a different domain, so getCsrfToken() always returned ""
    # and every mutating request received a 403.
    _samesite = "none" if _settings.app_env == "prod" else "lax"
    response.set_cookie(
        key="pulse_token",
        value=token,
        httponly=True,
        secure=True,
        samesite=_samesite,
        max_age=cookie_max_age,
        path="/",
    )

    if _settings.app_env == "prod":
        # Production: JWT only in httpOnly cookie, not in JSON body.
        return {"message": "ok"}

    # Dev mode: return token in response body (preserves `make dev` + test-suite flow).
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Clear auth and CSRF cookies."""
    response.delete_cookie("pulse_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(request: Request, session: AsyncSession = Depends(get_async_session)):
    user_id = await get_current_user(request=request, session=session)
    q = await session.get(User, user_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserSchema.model_validate(q.__dict__)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    """Dual-mode JWT auth dependency.

    Priority order:
    1. ``pulse_token`` httpOnly cookie — used in production (cookie-based auth).
    2. ``Authorization: Bearer <token>`` header — used in dev mode and the test suite.

    This allows the test suite (which uses Bearer headers) to work without cookies
    while production enforces httpOnly cookie auth.
    """
    token: str | None = None

    # 1. Cookie auth (production)
    cookie_token = request.cookies.get("pulse_token")
    if cookie_token:
        token = cookie_token
    else:
        # 2. Bearer header fallback (dev + tests)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            bearer = auth_header[7:]
            # Reject the frontend sentinel value "cookie" — it is never a real JWT.
            if bearer and bearer != "cookie":
                token = bearer

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = await session.get(User, sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return sub

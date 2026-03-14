import uuid

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.limiter import limiter
from ..core.security import create_access_token, decode_access_token, verify_password
from ..db.session import get_async_session
from ..models.user import User, UserSchema
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

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
async def login(request: Request, payload: LoginRequest, session: AsyncSession = Depends(get_async_session)):
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
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_async_session)):
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    q = await session.get(User, user_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserSchema.model_validate(q.__dict__)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return sub

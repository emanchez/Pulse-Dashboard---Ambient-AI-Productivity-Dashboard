from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import get_settings
from .db.base import Base
from .db.session import engine

settings = get_settings()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all registered models have their tables created (idempotent).
    # This covers newly added models (e.g. session_logs) without requiring
    # a manual migration step in development.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB tables verified/created via create_all")
    yield


app = FastAPI(title="Ambient AI Productivity Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# include routers (let import errors surface during startup)
from .api import auth as auth_router
from .api import tasks as tasks_router
from .api import stats as stats_router
from .api import sessions as sessions_router
from .api import reports as reports_router
from .api import system_states as system_states_router
from .middlewares.action_log import ActionLogMiddleware
from .models.session_log import SessionLog as _SessionLog  # noqa: F401 — register with Base.metadata
from .models.manual_report import ManualReport as _ManualReport  # noqa: F401 — register with Base.metadata
from .models.system_state import SystemState as _SystemState  # noqa: F401 — register with Base.metadata

app.include_router(auth_router.router)
app.include_router(tasks_router.router)
app.include_router(stats_router.router)
app.include_router(sessions_router.router, prefix="/sessions")
app.include_router(reports_router.router)
app.include_router(system_states_router.router)
app.add_middleware(ActionLogMiddleware)
logger.info("Routers and middleware wired")

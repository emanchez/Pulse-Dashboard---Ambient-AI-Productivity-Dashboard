from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

app = FastAPI(title="Ambient AI Productivity Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_cors_origins,
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
from .middlewares.action_log import ActionLogMiddleware

app.include_router(auth_router.router)
app.include_router(tasks_router.router)
app.include_router(stats_router.router)
app.add_middleware(ActionLogMiddleware)
logger.info("Routers and middleware wired")

# main.py (project root)
import os
import uvicorn
from fastapi import FastAPI
from src.routers.auth_router import router as auth_router
from src.routers.user_router import router as user_router
from src.routers.post_router import router as post_router
from src.routers.platforms_router import router as platforms_router
from src.infrastructure.database import init_db
from src.middleware.logging import RequestIdMiddleware
import structlog

def configure_structlog():
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
    )

configure_structlog()
logger = structlog.get_logger()

app = FastAPI(title="Social Scheduler")

app.add_middleware(RequestIdMiddleware)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(post_router)
app.include_router(platforms_router)

@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("app_startup")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)

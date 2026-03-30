"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .api.router import api_router


# Configure logging with timestamp and file info
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    log = logging.getLogger("app")
    log.info("服务启动 - 模型：%s, 并发限制：%d", settings.llm_model, settings.max_concurrent)
    yield
    log.info("服务关闭")


app = FastAPI(
    title="立体几何 3D 讲解生成服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all for development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing."""
    start = time.perf_counter()
    log = logging.getLogger("http")

    # Skip logging for static files and health checks
    path = request.url.path
    if not path.startswith("/lectures/") and path != "/health":
        log.info("← %s %s", request.method, path)

    try:
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000

        # Log response status
        if path != "/health":
            status_color = "→" if response.status_code < 400 else "✗"
            log.info("%s %s %s (%.0fms)", status_color, request.method, path, duration)

        return response
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        log.error("✗ %s %s (%.0fms): %s", request.method, path, duration, e)
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    log = logging.getLogger("app")
    log.exception("未处理异常：%s %s: %s", request.method, request.url.path, exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "detail": "服务器内部错误",
        },
    )


# API routes
app.include_router(api_router)

# Serve generated lectures as static files
os.makedirs(settings.lectures_dir, exist_ok=True)
app.mount("/lectures", StaticFiles(directory=settings.lectures_dir), name="lectures")

# Serve frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.llm_model}

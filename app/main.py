from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1 import media
from app.core.config import settings


# 2. Modern Lifespan Handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"--- {settings.APP_NAME} Starting Up ---")
    yield
    logger.info(f"--- {settings.APP_NAME} Shutting Down ---")


# 3. Initialize App
app = FastAPI(title=settings.get("APP_NAME", "StreamPulse"), lifespan=lifespan)


# 4. Global Exception Handler (Requirement: Handling proper exceptions)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "error": str(exc)},
    )


# 5. Include Routers
app.include_router(media.router, prefix="/api/v1/media", tags=["Media"])


@app.get("/health")
async def health():
    logger.info("Checking app health")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.get("HOST", settings.HOST),
        port=settings.get("PORT", settings.PORT),
        reload=settings.get("DEBUG", settings.DEBUG),
    )

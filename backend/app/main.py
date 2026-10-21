from fastapi import FastAPI

from app.api.routers.auth import (
    router as auth_router,
)
from app.api.routers.documents import (
    router as documents_router,
)


app = FastAPI(
    title="ReadFlow API",
    version="0.1.0",
)


app.include_router(
    documents_router
)
app.include_router(
    auth_router
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok"
    }

"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, dashboard, vendors
from .seed import seed

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-seed on startup so the 25-vendor master + demo users are always present
    # on launch. seed() is idempotent — it only inserts when the tables are empty,
    # so existing data and any vendors added during a demo are never touched.
    seed()
    yield


app = FastAPI(
    title="FinanceOS — Vendor Risk & Onboarding Screener",
    version="1.0.0",
    description="Process 3 of the FinanceOS technical assessment.",
    lifespan=lifespan,
)

# Vite dev server origins (design: runs locally, no production CORS needed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vendors.router)
app.include_router(dashboard.router)


@app.get("/api/health", tags=["health"])
def health():
    """Health + LLM-mode probe. `llm_enabled=false` means the app runs in rule-only
    fallback mode (no API key)."""
    return {"status": "ok", "llm_enabled": settings.llm_enabled, "model": settings.claude_model}

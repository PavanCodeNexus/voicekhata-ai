import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.session import setup_database
from app.api.routes import api_router
from app.voice.ws_voice import voice_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A hands-free, multilingual voice ledger for kirana stores. Built for Gnani Voice Hackathon (PS2)."
)

# Enable CORS for cross-origin local and cloud requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup hook to initialize SQLite with WAL mode and synthetic demo data
@app.on_event("startup")
def on_startup():
    setup_database()
    print(f"[{settings.PROJECT_NAME}] Database initialized at: {settings.DB_PATH}")

# Attach routers
app.include_router(api_router, prefix="/api")
app.include_router(voice_router)

# Mount frontend
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
frontend_dist = frontend_dir / "dist"
index_html = frontend_dir / "index.html"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    @app.get("/")
    def serve_frontend_dist():
        return FileResponse(str(frontend_dist / "index.html"))
elif index_html.exists():
    @app.get("/")
    def serve_frontend():
        return FileResponse(str(index_html))

@app.get("/api")
def root_api():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# -*- coding: utf-8 -*-
"""نقطة تشغيل تطبيق ProTrack Web API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, imports, locations, manuals, visits

app = FastAPI(title="ProTrack Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports.router)
app.include_router(locations.router)
app.include_router(manuals.router)
app.include_router(assets.router)
app.include_router(visits.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "protrack-web", "phase": 1}

# -*- coding: utf-8 -*-
"""نقطة تشغيل تطبيق ProTrack Web API."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import assets, cloud, imports, locations, manuals, rules, visits

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
app.include_router(rules.router)
app.include_router(cloud.router)
app.include_router(assets.router)
app.include_router(visits.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "protrack-web", "phase": 1}


# واجهة الويب المبنية (لوحة المهندس) — تُخدم من نفس الخادم إن وُجدت
if config.FRONTEND_DIST and Path(config.FRONTEND_DIST).is_dir():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="ui")

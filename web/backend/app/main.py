# -*- coding: utf-8 -*-
"""نقطة تشغيل تطبيق ProTrack Web API."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import ai, alerts, assets, cloud, imports, locations, manuals, rules, stock, visits, work_orders


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """دورة حياة الخادم: يشغّل السحب السحابي الدوري (لو مفعّل) ويوقفه عند الإغلاق."""
    from app.services.auto_pull import manager as auto_manager

    auto_manager.bootstrap()
    try:
        yield
    finally:
        auto_manager.shutdown()


app = FastAPI(title="ProTrack Web API", version="0.1.0", lifespan=lifespan)

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
app.include_router(alerts.router)
app.include_router(ai.router)
app.include_router(stock.router)
app.include_router(work_orders.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "protrack-web", "phase": 1}


# واجهة الويب المبنية (لوحة المهندس) — تُخدم من نفس الخادم إن وُجدت
if config.FRONTEND_DIST and Path(config.FRONTEND_DIST).is_dir():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="ui")

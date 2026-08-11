from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import discussions, guests, events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建数据库表"""
    init_db()
    yield


app = FastAPI(
    title="AI Panel Studio",
    description="AI 驱动的圆桌讨论 Web 应用",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS —— MVP 阶段允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(discussions.router)
app.include_router(guests.router)
app.include_router(events.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

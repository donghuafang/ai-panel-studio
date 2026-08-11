from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """创建所有表——在 app 启动时调用"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖注入：每个请求一个 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

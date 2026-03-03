from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.core.config import settings

# 优化数据库连接池配置
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,              # 减少连接池大小
    max_overflow=10,          # 减少最大溢出连接
    pool_recycle=3600,
    pool_pre_ping=True,       # 连接前检查有效性
    echo=False,
    connect_args={
        'connect_timeout': 5,  # 连接超时
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """获取数据库会话（用于非请求上下文）"""
    return SessionLocal()

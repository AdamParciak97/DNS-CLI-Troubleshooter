from __future__ import annotations
from sqlmodel import SQLModel, Session, create_engine
from cli_troubleshooter.config import get_settings

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = f"sqlite:///{settings.db_path}"
        _engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
    return _engine

def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session

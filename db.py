from collections.abc import Generator
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///biblioteca.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

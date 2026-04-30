from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # 🔥 important fix
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

# 🔥 recreate DB cleanly
Base.metadata.create_all(bind=engine)
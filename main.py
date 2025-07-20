from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

app = FastAPI()

# Ambil DATABASE_URL dari environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model DB
class PlayerDB(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(String, unique=True, index=True)
    username = Column(String)

# Buat tabel jika belum ada
Base.metadata.create_all(bind=engine)

# Model request
class Player(BaseModel):
    player_id: str
    username: str

@app.post("/register")
def register_player(player: Player):
    db = SessionLocal()
    existing = db.query(PlayerDB).filter(PlayerDB.player_id == player.player_id).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Player already registered")
    new_player = PlayerDB(player_id=player.player_id, username=player.username)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    db.close()
    return {"message": "Player registered successfully", "player": player}

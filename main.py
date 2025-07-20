from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import random
from dotenv import load_dotenv
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Setup DB
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define DB Models
class PlayerModel(Base):
    __tablename__ = "players"
    player_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI instance
app = FastAPI()

# DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In-memory items (bisa diganti ke DB nanti)
player_items = {
    "CRX001": {
        "username": "Crownless",
        "weapon": {
            "name": "Ironborn Sword",
            "upgrade_level": 10,
            "glow": False
        },
        "inventory": {
            "sigil_protection": 1
        }
    }
}

# Pydantic Schemas
class Player(BaseModel):
    player_id: str
    username: str

class UpgradeRequest(BaseModel):
    player_id: str
    item_type: str  # 'weapon'
    use_sigil: bool = False

class UpgradeResponse(BaseModel):
    success: bool
    new_upgrade_level: int = None
    glow: bool = False
    message: str

# Routes
@app.post("/register")
def register_player(player: Player, db: Session = Depends(get_db)):
    existing = db.query(PlayerModel).filter_by(player_id=player.player_id).first()
    if existing:
        return {"message": "Player already registered"}
    
    new_player = PlayerModel(player_id=player.player_id, username=player.username)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    return {"message": "Player registered successfully", "player": player}

@app.post("/upgrade", response_model=UpgradeResponse)
def upgrade_item(req: UpgradeRequest):
    player = player_items.get(req.player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    item = player.get(req.item_type)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    level = item["upgrade_level"]
    if level >= 15:
        return UpgradeResponse(success=False, message="Max level reached")
    
    # Upgrade chance
    def calc_chance(lvl):
        if lvl <= 5:
            return 1.0
        elif lvl <= 10:
            return 0.85 - (lvl - 6) * 0.05
        elif lvl == 11: return 0.3
        elif lvl == 12: return 0.25
        elif lvl == 13: return 0.2
        elif lvl == 14: return 0.15
        elif lvl == 15: return 0.1
        return 0

    chance = calc_chance(level + 1)
    success = random.random() <= chance

    if success:
        item["upgrade_level"] += 1
        item["glow"] = item["upgrade_level"] >= 11
        return UpgradeResponse(
            success=True,
            new_upgrade_level=item["upgrade_level"],
            glow=item["glow"],
            message=f"Upgrade success! {item['name']} is now +{item['upgrade_level']}"
        )
    else:
        if level >= 11:
            if req.use_sigil and player["inventory"]["sigil_protection"] > 0:
                player["inventory"]["sigil_protection"] -= 1
                return UpgradeResponse(success=False, message="Upgrade failed but item protected by Sigil.")
            else:
                item["upgrade_level"] -= 1
                item["glow"] = item["upgrade_level"] >= 11
                return UpgradeResponse(success=False, message=f"Upgrade failed. Item downgraded to +{item['upgrade_level']}")
        return UpgradeResponse(success=False, message="Upgrade failed.")

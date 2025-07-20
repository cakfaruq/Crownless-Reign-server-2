from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
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
    weapon = relationship("WeaponModel", back_populates="player", uselist=False)
    inventory = relationship("InventoryModel", back_populates="player", uselist=False)

class WeaponModel(Base):
    __tablename__ = "weapons"
    player_id = Column(String, ForeignKey("players.player_id"), primary_key=True)
    name = Column(String, default="Ironborn Sword")
    upgrade_level = Column(Integer, default=0)
    glow = Column(Boolean, default=False)
    player = relationship("PlayerModel", back_populates="weapon")

class InventoryModel(Base):
    __tablename__ = "inventories"
    player_id = Column(String, ForeignKey("players.player_id"), primary_key=True)
    sigil_protection = Column(Integer, default=0)
    player = relationship("PlayerModel", back_populates="inventory")

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
    new_weapon = WeaponModel(player_id=player.player_id, upgrade_level=10)
    new_inventory = InventoryModel(player_id=player.player_id, sigil_protection=1)
    
    db.add(new_player)
    db.add(new_weapon)
    db.add(new_inventory)
    db.commit()

    return {"message": "Player registered successfully", "player": player}

@app.post("/upgrade", response_model=UpgradeResponse)
def upgrade_item(req: UpgradeRequest, db: Session = Depends(get_db)):
    player = db.query(PlayerModel).filter_by(player_id=req.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    weapon = db.query(WeaponModel).filter_by(player_id=req.player_id).first()
    inventory = db.query(InventoryModel).filter_by(player_id=req.player_id).first()

    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")

    level = weapon.upgrade_level
    if level >= 15:
        return UpgradeResponse(success=False, message="Max level reached")

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
        weapon.upgrade_level += 1
        weapon.glow = weapon.upgrade_level >= 11
        db.commit()
        return UpgradeResponse(
            success=True,
            new_upgrade_level=weapon.upgrade_level,
            glow=weapon.glow,
            message=f"Upgrade success! {weapon.name} is now +{weapon.upgrade_level}"
        )
    else:
        if level >= 11:
            if req.use_sigil and inventory.sigil_protection > 0:
                inventory.sigil_protection -= 1
                db.commit()
                return UpgradeResponse(success=False, message="Upgrade failed but item protected by Sigil.")
            else:
                weapon.upgrade_level -= 1
                weapon.glow = weapon.upgrade_level >= 11
                db.commit()
                return UpgradeResponse(success=False, message=f"Upgrade failed. Item downgraded to +{weapon.upgrade_level}")
        return UpgradeResponse(success=False, message="Upgrade failed.")

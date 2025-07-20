from sqlalchemy import Column, String
from database import Base

class PlayerModel(Base):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)

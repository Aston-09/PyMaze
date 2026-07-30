from app.models.player import PlayerState
from app.db import saves_collection
from motor.motor_asyncio import AsyncIOMotorCollection

async def save_game(player: PlayerState, username: str) -> bool:
    """Save the player state to MongoDB."""
    player_data = player.model_dump()
    player_data["username"] = username
    
    await saves_collection.update_one(
        {"username": username},
        {"$set": player_data},
        upsert=True
    )
    return True

async def load_game(username: str) -> PlayerState | None:
    """Load player state from MongoDB. Returns None if not found."""
    data = await saves_collection.find_one({"username": username})
    if not data:
        return None
        
    # Remove MongoDB's internal _id and our added username field before initializing PlayerState
    data.pop("_id", None)
    data.pop("username", None)
    
    return PlayerState(**data)

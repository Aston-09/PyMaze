"""Persistence for users and saves.

Set MONGODB_URI and everything goes to MongoDB, with failures raised rather
than swallowed. Leave it unset and the whole game runs off a single JSON file
under backend/saves/ — fine on one dev machine, not for a deploy.

The previous version tried both at once: a 1-second budget on the Mongo call
and a silent fall-through to the JSON file on any error. An Atlas cold start
(SRV DNS lookup + TLS handshake) routinely needs more than a second, so the
first request quietly timed out, the client was discarded for the rest of the
process, and every write landed in a local file the deployed app never reads.
From the outside that looks exactly like "the database isn't running".
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB = os.getenv("MONGODB_DB", "pymaze")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVES_DIR = os.path.join(BASE_DIR, "saves")
LOCAL_DB_FILE = os.path.join(SAVES_DIR, "local_db.json")


class LocalJsonCollection:
    """A Mongo-shaped view over one key of a single JSON file.

    ponytail: whole-file read/write per operation and no locking. It only ever
    backs single-machine development; anything concurrent should set
    MONGODB_URI.
    """

    def __init__(self, name: str):
        self.name = name

    def _load_data(self) -> list:
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get(self.name, [])
        except (OSError, json.JSONDecodeError):
            return []

    def _save_data(self, collection_data: list) -> None:
        os.makedirs(SAVES_DIR, exist_ok=True)
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            db_data = {}
        db_data[self.name] = collection_data
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2)

    @staticmethod
    def _matches(doc: dict, filter: dict) -> bool:
        return all(doc.get(k) == v for k, v in filter.items())

    async def find_one(self, filter: dict) -> dict | None:
        for doc in self._load_data():
            if self._matches(doc, filter):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict) -> None:
        data = self._load_data()
        data.append(dict(doc))
        self._save_data(data)

    async def update_one(self, filter: dict, update: dict, upsert: bool = False) -> None:
        data = self._load_data()
        set_data = update.get("$set", {})
        for doc in data:
            if self._matches(doc, filter):
                doc.update(set_data)
                break
        else:
            if not upsert:
                return
            data.append({**filter, **set_data})
        self._save_data(data)


_client = None


def _mongo_collection(name: str):
    global _client
    if _client is None:
        from pymongo import AsyncMongoClient
        _client = AsyncMongoClient(MONGODB_URI, serverSelectionTimeoutMS=15000)
    return _client[MONGODB_DB][name]


class Collection:
    """Whichever backing store this deployment configured, same three calls."""

    def __init__(self, name: str):
        self.name = name
        self._local = None if MONGODB_URI else LocalJsonCollection(name)

    def _target(self):
        return self._local if self._local is not None else _mongo_collection(self.name)

    async def find_one(self, filter: dict) -> dict | None:
        return await self._target().find_one(filter)

    async def insert_one(self, doc: dict) -> None:
        await self._target().insert_one(doc)

    async def update_one(self, filter: dict, update: dict, upsert: bool = False) -> None:
        await self._target().update_one(filter, update, upsert=upsert)


users_collection = Collection("users")
saves_collection = Collection("saves")


async def connect() -> str:
    """Prove the configured store works, at boot rather than at first login.

    Returns a one-line description for the startup log.
    """
    if not MONGODB_URI:
        os.makedirs(SAVES_DIR, exist_ok=True)
        return f"local JSON store at {LOCAL_DB_FILE} (set MONGODB_URI for a real database)"

    await _mongo_collection("users").database.client.admin.command("ping")
    # One username per account, enforced by the database rather than by the
    # read-then-insert in the register route, which two requests can interleave.
    await _mongo_collection("users").create_index("username", unique=True)
    await _mongo_collection("saves").create_index("username", unique=True)
    return f"MongoDB database '{MONGODB_DB}'"

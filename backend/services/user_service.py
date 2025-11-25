from __future__ import annotations
import time
from typing import Optional, Dict, Any
from bson import ObjectId
from backend.services.db_service import get_db
from backend.utils.auth import hash_password, verify_password, hash_refresh_token

class UserService:
    def __init__(self):
        self.db = get_db()
        self.users = self.db["users"]
        self.sessions = self.db["sessions"]
        # Creating indexes can trigger network calls to MongoDB. Guard these
        # so importing modules (e.g. during pytest collection) doesn't fail
        # when a Mongo instance isn't available.
        try:
            self.users.create_index("email", unique=True)
            self.sessions.create_index("user_id")
            self.sessions.create_index("refresh_hash")
        except Exception:
            # Index creation failed or DB is unreachable at import time.
            # Tests or the runtime environment can create/index later or
            # mock DB interactions as needed.
            pass

    def create_user(self, email: str, password: str) -> Dict[str, Any]:
        now = int(time.time())
        doc = {
            "email": email.lower().strip(),
            "password_hash": hash_password(password),
            "email_verified": False,
            "roles": ["user"],
            "created_at": now,
            "updated_at": now,
            "profile": {},
        }
        res = self.users.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"email": email.lower().strip()})

    def verify_user_password(self, user: Dict[str, Any], password: str) -> bool:
        return verify_password(password, user.get("password_hash", ""))

    def create_session(self, user_id: ObjectId, refresh_token: str, user_agent: str = "", ip: str = "") -> Dict[str, Any]:
        now = int(time.time())
        doc = {
            "user_id": user_id,
            "refresh_hash": hash_refresh_token(refresh_token),
            "created_at": now,
            "user_agent": user_agent,
            "ip": ip,
        }
        self.sessions.insert_one(doc)
        return doc

    def get_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        return self.sessions.find_one({"refresh_hash": hash_refresh_token(refresh_token)})

    def delete_session(self, refresh_token: str) -> None:
        self.sessions.delete_one({"refresh_hash": hash_refresh_token(refresh_token)})

    def update_user(self, user_id: ObjectId, updates: Dict[str, Any]) -> bool:
        try:
            # Filter allowed updates
            allowed = {"profile", "settings", "api_keys"} # Add api_keys here or inside profile
            filtered = {k: v for k, v in updates.items() if k in allowed}
            if not filtered:
                return False
            
            # Special handling for nested profile updates if needed, but $set is fine for now
            self.users.update_one(
                {"_id": user_id},
                {"$set": {**filtered, "updated_at": int(time.time())}}
            )
            return True
        except Exception:
            return False

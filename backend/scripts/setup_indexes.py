"""
MongoDB index setup for Phase 2 collections.
Run once after deployment.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(".env.development")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "learnlab")

def setup_indexes():
    """Create indexes for optimal query performance"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    print("Setting up MongoDB indexes for Phase 2...")
    
    # Learning Plans indexes
    print("Creating learning_plans indexes...")
    db["learning_plans"].create_index("user_id")
    db["learning_plans"].create_index([("user_id", 1), ("status", 1)])
    db["learning_plans"].create_index("created_at")
    print("✓ learning_plans indexes created")
    
    # User Progress indexes
    print("Creating user_progress indexes...")
    db["user_progress"].create_index([("user_id", 1), ("plan_id", 1)], unique=True)
    db["user_progress"].create_index("plan_id")
    print("✓ user_progress indexes created")
    
    # Schedules indexes
    print("Creating schedules indexes...")
    db["schedules"].create_index([("user_id", 1), ("plan_id", 1)], unique=True)
    db["schedules"].create_index("plan_id")
    print("✓ schedules indexes created")
    
    # Reminders indexes
    print("Creating reminders indexes...")
    db["reminders"].create_index("plan_id")
    db["reminders"].create_index([("enabled", 1), ("schedule", 1)])
    print("✓ reminders indexes created")
    
    # iCal Tokens (TTL: 90 days = 7776000 seconds)
    print("Creating ical_tokens indexes...")
    db["ical_tokens"].create_index("created_at", expireAfterSeconds=7776000)
    print("✓ ical_tokens indexes created (with 90-day TTL)")
    
    print("\n✅ All Phase 2 indexes created successfully!")
    client.close()

if __name__ == "__main__":
    setup_indexes()

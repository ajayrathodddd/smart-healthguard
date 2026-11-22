import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]


async def connect_to_mongodb():
    await client.admin.command("ping")
    print("MongoDB connected successfully!")


async def close_mongodb_connection():
    client.close()
    print("MongoDB connection closed.")
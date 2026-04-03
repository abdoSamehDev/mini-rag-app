from fastapi import FastAPI
from routes import base_router, data_router
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from helpers import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup app
    settings = get_settings()
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DB_NAME]
    yield
    # shutdown app
    app.mongo_conn.close()


app = FastAPI(lifespan=lifespan)

app.include_router(base_router)
app.include_router(data_router)

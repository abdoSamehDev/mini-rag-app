from fastapi import FastAPI
from routes import base_router, data_router
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from helpers import get_settings
from stores import LLMProviderFactory, VectorDBProviderFactory


async def startup_span(app: FastAPI):
    settings = get_settings()

    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DB_NAME]

    llm_provider_factory = LLMProviderFactory(config=settings)
    vector_db_provider_factory = VectorDBProviderFactory(config=settings)

    # generation client
    app.generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEDND
    )
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    # embedding client
    app.embedding_client = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEDND
    )
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID, model_size=settings.EMBEDDING_MODEL_SIZE
    )
    # vector db client
    app.vector_db_client = vector_db_provider_factory.create(settings.VECTOR_DB_BACKEND)
    app.vector_db_client.connect()


async def shutdown_span(app: FastAPI):
    app.mongo_conn.close()
    # vector db client
    app.vector_db_client.disconnect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup app
    startup_span(app)
    # shutdown app
    yield
    shutdown_span(app)


app = FastAPI(lifespan=lifespan)


app.include_router(base_router)
app.include_router(data_router)

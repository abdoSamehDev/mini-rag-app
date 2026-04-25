from fastapi import FastAPI
from routes import base_router, data_router, nlp_router
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from helpers import get_settings
from stores import LLMProviderFactory, VectorDBProviderFactory, TemplateParser
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def startup_span(app: FastAPI):
    settings = get_settings()

    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    # app.db_client = app.mongo_conn[settings.MONGODB_DB_NAME]

    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"

    app.db_engine = create_async_engine(postgres_conn)
    app.db_client = sessionmaker(
        app.db_engine, class_=AsyncSession, expire_on_commit=False
    )

    llm_provider_factory = LLMProviderFactory(config=settings)
    vector_db_provider_factory = VectorDBProviderFactory(
        config=settings, db_client=app.db_client
    )

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
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )
    # vector db client
    app.vector_db_client = vector_db_provider_factory.create(settings.VECTOR_DB_BACKEND)
    await app.vector_db_client.connect()

    # locales
    app.template_parser = TemplateParser(
        default_language=settings.DEFAULT_LANG, language=settings.PRIMARY_LANG
    )


async def shutdown_span(app: FastAPI):
    app.mongo_conn.close()
    # vector db client
    await app.vector_db_client.disconnect()
    # postgres
    await app.db_engine.dispose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup app
    await startup_span(app)
    # shutdown app
    yield
    await shutdown_span(app)


app = FastAPI(lifespan=lifespan)


app.include_router(base_router)
app.include_router(data_router)
app.include_router(nlp_router)

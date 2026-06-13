from celery import Celery
from helpers import get_settings

from stores import LLMProviderFactory, VectorDBProviderFactory, TemplateParser
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# load settings
settings = get_settings()


async def get_setup_utils():
    # load settings
    settings = get_settings()

    # mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    # db_client = mongo_conn[settings.MONGODB_DB_NAME]

    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"

    db_engine = create_async_engine(postgres_conn)
    db_client = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    llm_provider_factory = LLMProviderFactory(config=settings)
    vector_db_provider_factory = VectorDBProviderFactory(
        config=settings, db_client=db_client
    )

    # generation client
    generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEDND
    )
    generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    # embedding client
    embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEDND)
    embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )
    # vector db client
    vector_db_client = vector_db_provider_factory.create(settings.VECTOR_DB_BACKEND)
    await vector_db_client.connect()

    # locales
    template_parser = TemplateParser(
        default_language=settings.DEFAULT_LANG, language=settings.PRIMARY_LANG
    )

    return (
        db_engine,
        db_client,
        llm_provider_factory,
        vector_db_provider_factory,
        generation_client,
        embedding_client,
        vector_db_client,
        template_parser,
    )


# Create Celery application instance
celery_app = Celery(
    "minirag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.file_processing"],
)

# Configure Celery with essential settings
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_TASK_SERIALIZER],
    # Task safety - Late acknowledgment prevents task loss on worker crash
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    # Time limits - Prevent hanging tasks
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    # Result backend - Store results for status tracking
    task_ignore_resul=False,
    result_expires=3600,
    # Worker settings
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    # Connection settings for better reliability
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_routes={
        "tasks.file_processing.process_project_files": {"queue": "file_processing"},
        "tasks.data_indexing.index_data_content": {"queue": "data_indexing"},
        "tasks.maintenance.clean_celery_executions_table": {"queue": "default"},
        "tasks.process_workflow.process_and_push_workflow": {
            "queue": "file_processing"
        },
    },
    beat_schedule={
        "cleanup-old-task-records": {
            "task": "tasks.maintenance.clean_celery_executions_table",
            "schedule": 60,
            "args": (),
        }
    },
    timezone="UTC",
)

celery_app.conf.task_default_queue = "default"

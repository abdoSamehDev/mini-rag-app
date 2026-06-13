from celery_app import celery_app, get_setup_utils


from controllers import (
    ProcessController,
    ProjectDBController,
    ChunkDBController,
    AssetDBController,
    NLPController,
)

from models import (
    ResponseMessageEnums,
    PgChunk as Chunk,
    AssetTypeEnums,
)
from utils import IdempotencyManager
from helpers import get_settings
import asyncio
import logging

logger = logging.getLogger(__name__)


def get_process_controller(project_id: int):
    return ProcessController(project_id=project_id)


@celery_app.task(
    bind=True,
    name="tasks.file_processing.process_project_files",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def process_project_files(
    self,
    project_id: int,
    file_id: int,
    chunk_size: int,
    overlap_size: int,
    do_reset: int,
):

    return asyncio.run(
        _process_project_files(
            self, project_id, file_id, chunk_size, overlap_size, do_reset
        )
    )


async def _process_project_files(
    task_instance,
    project_id: int,
    file_id: int,
    chunk_size: int,
    overlap_size: int,
    do_reset: int,
):
    db_engine, vector_db_client = None, None
    try:
        (
            db_engine,
            db_client,
            llm_provider_factory,
            vectordb_provider_factory,
            generation_client,
            embedding_client,
            vector_db_client,
            template_parser,
        ) = await get_setup_utils()

        # setup request and controllers
        project_db_controller = await ProjectDBController.create_instance(db_client)
        asset_db_controller = await AssetDBController.create_instance(db_client)
        chunk_db_controller = await ChunkDBController.create_instance(db_client)
        nlp_controller = NLPController(
            vectordb_client=vector_db_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        process_controller = get_process_controller(project_id=project_id)

        # Create idempotency manager
        idempotency_manager = IdempotencyManager(db_client, db_engine)

        task_args = {
            "project_id": project_id,
            "file_id": file_id,
            "chunk_size": chunk_size,
            "overlap_size": overlap_size,
            "do_reset": do_reset,
        }

        task_name = "tasks.file_processing.process_project_files"

        settings = get_settings()

        # Check if task should execute (600 seconds = 10 minutes timeout)
        should_execute, existing_task = await idempotency_manager.should_execute_task(
            task_name=task_name,
            task_args=task_args,
            # celery_task_id=task_instance.request.id,
            task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
        )
        logger.warning(
            f"should_execute: {should_execute} | existing_task: {existing_task}"
        )

        if not should_execute:
            logger.warning(f"Can not handle the task | status: {existing_task.status}")
            return existing_task.result

        task_record = None

        if existing_task:
            # Update existing task with new celery task ID
            await idempotency_manager.update_task_status(
                execution_id=existing_task.execution_id, status="PENDING"
            )
            task_record = existing_task

        else:
            # Create new task record
            task_record = await idempotency_manager.create_task_record(
                celery_task_id=task_instance.request.id,
                task_name=task_name,
                task_args=task_args,
            )

        # Update status to STARTED
        await idempotency_manager.update_task_status(
            execution_id=task_record.execution_id,
            status="STARTED",
        )

        # get the project from db
        project = await project_db_controller.get_project_or_create_one(
            project_id=project_id
        )
        # get file to process
        project_files_ids = {}
        if file_id:
            logger.warning(
                f"Processing specific file_id: {file_id} with project_id: {project_id}"
            )
            asset_record = await asset_db_controller.get_asset_record(
                # asset_name=file_id, project_id=project_id
                asset_project_id=project.project_id,
                asset_name=file_id,
            )
            if asset_record is None:
                task_instance.update_state(
                    statue="FAILURE",
                    meta={"message": ResponseMessageEnums.FILE_ID_ERROR.value},
                )

                # Update task status to FAILURE
                await idempotency_manager.update_task_status(
                    execution_id=task_record.execution_id,
                    status="FAILURE",
                    result={"message": ResponseMessageEnums.FILE_ID_ERROR.value},
                )

                raise Exception(ResponseMessageEnums.FILE_ID_ERROR.value)

            project_files_ids = {asset_record.asset_id: asset_record.asset_name}
        else:
            project_files = await asset_db_controller.get_all_project_assets(
                asset_project_id=project_id,
                asset_type=AssetTypeEnums.FILE.value,
            )

            project_files_ids = {
                record.asset_id: record.asset_name for record in project_files
            }

        if not project_files_ids or len(project_files_ids) == 0:
            task_instance.update_state(
                statue="FAILURE",
                meta={"message": ResponseMessageEnums.NO_FILES_ERROR.value},
            )
            # Update task status to FAILURE
            await idempotency_manager.update_task_status(
                execution_id=task_record.execution_id,
                status="FAILURE",
                result={"message": ResponseMessageEnums.NO_FILES_ERROR.value},
            )

            raise Exception(ResponseMessageEnums.NO_FILES_ERROR.value)

        # reset chunks if needed
        if do_reset == 1:
            # Delete the associated vectors collection
            collection_name = nlp_controller.create_collection_name(
                project_id=project_id
            )
            # logger.warning(f"Deleting collection: {collection_name}")
            _ = await vector_db_client.delete_collection(
                collection_name=collection_name
            )

            # Delete the associated chunks
            _ = await chunk_db_controller.delete_chunks_by_project_id(
                project_id=project_id
            )

        # process files
        no_record = 0
        no_files = 0

        try:
            for asset_id, file_id in project_files_ids.items():
                file_content = process_controller.get_file_content(file_id=file_id)
                if file_content is None:
                    logger.error(f"No content found for file_id: {file_id}")
                    continue
                file_chunks = process_controller.process_file_content(
                    chunk_size=chunk_size,
                    overlap_size=overlap_size,
                    file_content=file_content,
                )

                if file_chunks is None or len(file_chunks) == 0:
                    logger.error(f"Error while chunking file: {file_id}")
                    continue

                file_chunks_records = [
                    Chunk(
                        chunk_text=chunk.page_content,
                        chunk_metadata=chunk.metadata,
                        chunk_project_id=project_id,
                        chunk_asset_id=asset_id,
                        chunk_order=i + 1,
                    )
                    for i, chunk in enumerate(file_chunks)
                ]
                no_record += await chunk_db_controller.insert_many_chunks(
                    chunks=file_chunks_records
                )
                no_files += 1
            task_instance.update_state(
                statue="SUCCESS",
                meta={"message": ResponseMessageEnums.PROCESSING_SUCCESS.value},
            )

            # Update task status to SUCCESS
            await idempotency_manager.update_task_status(
                execution_id=task_record.execution_id,
                status="SUCCESS",
                result={"message": ResponseMessageEnums.PROCESSING_SUCCESS.value},
            )

            # logger.info(f"inserted_chunks: {no_record}")
            logger.warning(f"inserted_chunks: {no_record}")
            # logger.error(f"inserted_chunks: {no_record}")

            return (
                {
                    "message": ResponseMessageEnums.PROCESSING_SUCCESS.value,
                    "inserted_records": no_record,
                    "processed_files": no_files,
                    "project_id": project_id,
                    "do_reset": do_reset,
                },
            )

        except Exception as e:
            task_instance.update_state(
                statue="FAILURE",
                meta={"message": ResponseMessageEnums.PROCESSING_FAILED.value},
            )
            raise Exception(f"{ResponseMessageEnums.PROCESSING_FAILED.value}: {e}")

    except Exception as e:
        logger.error(f"Task Failed: {str(e)}")
        raise
    finally:
        try:
            if db_engine:
                await db_engine.dispose()

            if vector_db_client:
                await vector_db_client.disconnect()
        except Exception as e:
            logger.error(f"Task Failed While Cleanning: {str(e)}")

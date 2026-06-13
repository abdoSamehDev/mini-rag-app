from celery_app import celery_app, get_setup_utils


from controllers import (
    ProjectDBController,
    ChunkDBController,
    NLPController,
)

from models import (
    ResponseMessageEnums,
)

from tqdm.auto import tqdm
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.data_indexing.index_data_content",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def index_data_content(self, project_id: int, do_reset: int):
    logger.warning("index_data_content started")
    return asyncio.run(_index_data_content(self, project_id, do_reset))


async def _index_data_content(task_instance, project_id: int, do_reset: int):
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

        logger.warning("Setup utils were loaded!")

        # setup request and controllers
        project_db_controller = await ProjectDBController.create_instance(db_client)
        chunk_db_controller = await ChunkDBController.create_instance(db_client)
        nlp_controller = NLPController(
            vectordb_client=vector_db_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        project = await project_db_controller.get_project_or_create_one(
            project_id=project_id
        )

        if not project:
            task_instance.update_state(
                state="FAILURE",
                meta={"message": ResponseMessageEnums.PROJECT_NOT_FOUND_ERROR.value},
            )

            raise Exception(f"No project found for project_id: {project_id}")

        has_records = True
        page_no = 1
        inserted_items_count = 0
        idx = 0

        # create collection if not exists
        collection_name = nlp_controller.create_collection_name(project_id=project_id)

        _ = await db_client.create_collection(
            collection_name=collection_name,
            embedding_size=embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # setup batching
        total_chunks_count = await chunk_db_controller.get_total_chunks_count(
            project_id=project_id
        )

        logger.info(f"Total chunks for {collection_name}: {total_chunks_count}")
        pbar = tqdm(total=total_chunks_count, desc="Vector Indexing", position=0)

        while has_records:
            logger.info(f"Getting project chunks for project id: {project_id}")
            page_chunks = await chunk_db_controller.get_project_chunks(
                project_id=project.project_id, page_no=page_no
            )
            logger.info(
                f"Processing page {page_no} with {len(page_chunks)} chunks for project_id: {project_id}"
            )
            if len(page_chunks):
                page_no += 1
            if not page_chunks or len(page_chunks) == 0:
                has_records = False
                break

            chunk_ids = [c.chunk_id for c in page_chunks]
            idx += len(page_chunks)

            is_inserted = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=page_chunks,
                chunk_ids=chunk_ids,
            )

            if not is_inserted:
                task_instance.update_state(
                    state="FAILURE",
                    meta={
                        "message": ResponseMessageEnums.INSERT_INTO_VECTORDB_ERROR.value
                    },
                )
                raise Exception(
                    f"can not insert into vectorDB | project_id: {project_id}"
                )

            pbar.update(len(page_chunks))
            inserted_items_count += len(page_chunks)

        task_instance.update_state(
            state="SUCCESS",
            meta={"message": ResponseMessageEnums.INSERT_INTO_VECTORDB_SUCCESS.value},
        )
        return {
            "message": ResponseMessageEnums.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        }
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise
    finally:
        try:
            if db_engine:
                await db_engine.dispose()

            if vector_db_client:
                await vector_db_client.disconnect()
        except Exception as e:
            logger.error(f"Task failed while cleaning: {str(e)}")

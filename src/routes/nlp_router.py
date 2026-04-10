from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from controllers import ProjectDBController, ChunkDBController, NLPController
from models import ResponseMessageEnums
from .schemes import PushRequest, SearchRequest
from helpers import get_logger

nlp_router = APIRouter(prefix="/api/v1/nlp", tags=["api_v1", "nlp"])

logger = get_logger()


@nlp_router.post("/index/push/{project_id}")
async def index_project(req: Request, project_id: str, push_request: PushRequest):
    project_db_controller = await ProjectDBController.create_instance(
        db_client=req.app.db_client
    )

    chunk_db_controller = await ChunkDBController.create_instance(
        db_client=req.app.db_client
    )

    nlp_controller = NLPController(
        vectordb_client=req.app.vector_db_client,
        embedding_client=req.app.embedding_client,
        generation_client=req.app.generation_client,
        template_parser=req.app.template_parser,
    )

    project = await project_db_controller.get_project_or_create_one(
        project_id=project_id
    )

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.PROJECT_NOT_FOUND_ERROR.value},
        )

    has_records = True
    page_no = 1
    inserted_items_count = 0
    idx = 0
    while has_records:
        page_chunks = await chunk_db_controller.get_project_chunks(
            project_id=project.id, page_no=page_no
        )
        if len(page_chunks):
            page_no += 1
        if not page_chunks or len(page_chunks) == 0:
            has_records = False
            break

        chunk_ids = list(range(idx, idx + len(page_chunks)))
        idx += len(page_chunks)

        is_inserted = nlp_controller.index_into_vector_db(
            project=project,
            chunks=page_chunks,
            chunk_ids=chunk_ids,
            do_reset=push_request.do_reset,
        )

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": ResponseMessageEnums.INSERT_INTO_VECTORDB_ERROR.value
                },
            )
        inserted_items_count += len(page_chunks)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": ResponseMessageEnums.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        },
    )


@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(req: Request, project_id: str):
    project_db_controller = await ProjectDBController.create_instance(
        db_client=req.app.db_client
    )

    nlp_controller = NLPController(
        vectordb_client=req.app.vector_db_client,
        embedding_client=req.app.embedding_client,
        generation_client=req.app.generation_client,
        template_parser=req.app.template_parser,
    )

    project = await project_db_controller.get_project_or_create_one(
        project_id=project_id
    )

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.PROJECT_NOT_FOUND_ERROR.value},
        )
    collection_info = nlp_controller.get_vector_db_collection_info(project=project)

    if not collection_info:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": ResponseMessageEnums.VECTORDB_COLLECTION_RETRIEVED_ERROR.value
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": ResponseMessageEnums.VECTORDB_COLLECTION_RETRIEVED_SUCCESS.value,
            "collection_info": collection_info,
        },
    )


@nlp_router.post("/index/search/{project_id}")
async def search_index(req: Request, project_id: str, search_req: SearchRequest):
    project_db_controller = await ProjectDBController.create_instance(
        db_client=req.app.db_client
    )

    nlp_controller = NLPController(
        vectordb_client=req.app.vector_db_client,
        embedding_client=req.app.embedding_client,
        generation_client=req.app.generation_client,
        template_parser=req.app.template_parser,
    )

    project = await project_db_controller.get_project_or_create_one(
        project_id=project_id
    )

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.PROJECT_NOT_FOUND_ERROR.value},
        )

    results = nlp_controller.search_vector_db_collection(
        project=project, text=search_req.text, limit=search_req.limit
    )

    if not results or len(results) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.VECTORDB_SEARCH_ERROR.value},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": ResponseMessageEnums.VECTORDB_SEARCH_SUCCESS.value,
            "results": [result.dict() for result in results],
        },
    )


@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(req: Request, project_id: str, search_req: SearchRequest):
    logger.info("WORKING!!!!!")
    project_db_controller = await ProjectDBController.create_instance(
        db_client=req.app.db_client
    )

    nlp_controller = NLPController(
        vectordb_client=req.app.vector_db_client,
        embedding_client=req.app.embedding_client,
        generation_client=req.app.generation_client,
        template_parser=req.app.template_parser,
    )

    project = await project_db_controller.get_project_or_create_one(
        project_id=project_id
    )

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.PROJECT_NOT_FOUND_ERROR.value},
        )

    answer, full_prompt, chat_history = nlp_controller.asnwer_rag_question(
        project=project, query=search_req.text, limit=search_req.limit
    )
    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.RAG_ANSWER_ERROR.value},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": ResponseMessageEnums.RAG_ANSWER_SUCCESS.value,
                "answer": answer,
                "full_prompt": full_prompt,
                "chat_history": chat_history,
            },
        )

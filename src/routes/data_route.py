import os
from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import aiofiles
from controllers import (
    DataController,
    ProjectController,
    ProcessController,
    ProjectDBController,
    ChunkDBController,
    AssetDBController,
    NLPController,
)
from helpers import get_settings, Settings, get_logger
from models import (
    ResponseMessageEnums,
    PgChunk as Chunk,
    PgAsset as Asset,
    AssetTypeEnums,
)
from .schemes import ProcessRequest

data_router = APIRouter(prefix="/api/v1/data", tags=["api_v1", "data"])

logger = get_logger()


def get_data_controller():
    return DataController()


def get_project_controller():
    return ProjectController()


def get_process_controller(project_id: int):
    return ProcessController(project_id=project_id)


@data_router.post("/upload/{project_id}")
async def upload_file(
    request: Request,
    project_id: int,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
    data_controller: DataController = Depends(get_data_controller),
):
    project_db_controller = await ProjectDBController.create_instance(
        request.app.db_client
    )
    asset_db_controller = await AssetDBController.create_instance(request.app.db_client)

    project = await project_db_controller.get_project_or_create_one(
        project_id=project_id
    )

    # validate the file
    is_valid, message = data_controller.validate_uplaoded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"message": message}
        )

    # generate unique file path
    file_path, file_id = data_controller.generate_unique_file_path(
        orignal_file_name=file.filename, project_id=project_id
    )

    # save the file
    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:
        logger.error(f"Error saving file: {e}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.FILE_UPLOAD_FAILED.value},
        )

    # store asset into the db
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_name=file_id,
        asset_type=AssetTypeEnums.FILE.value,
        asset_size=os.path.getsize(file_path),
    )

    asset_record = await asset_db_controller.create_asset(asset=asset_resource)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": ResponseMessageEnums.FILE_UPLOAD_SUCCESS.value,
            "file_id": str(asset_record.asset_id),
        },
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(
    request: Request,
    project_id: int,
    process_request: ProcessRequest,
):
    # setup request and controllers
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    project_db_controller = await ProjectDBController.create_instance(
        request.app.db_client
    )
    asset_db_controller = await AssetDBController.create_instance(request.app.db_client)
    chunk_db_controller = await ChunkDBController.create_instance(request.app.db_client)
    nlp_controller = NLPController(
        vectordb_client=request.app.vector_db_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    process_controller = get_process_controller(project_id=project_id)

    # get the project from db
    project = await project_db_controller.get_project_or_create_one(
        project_id=project_id
    )
    # get file to process
    project_files_ids = {}
    if file_id:
        logger.info(
            f"Processing specific file_id: {file_id} with project_id: {project_id}"
        )
        asset_record = await asset_db_controller.get_asset_record(
            # asset_name=file_id, project_id=project_id
            asset_project_id=project_id,
            asset_name=file_id,
        )
        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": ResponseMessageEnums.FILE_ID_ERROR.value},
            )
        project_files_ids = {asset_record.asset_id: asset_record.asset_name}
    else:
        project_files = await asset_db_controller.get_all_project_assets(
            asset_project_id=project_id,
            asset_type=AssetTypeEnums.FILE.value,
        )
        logger.info(
            f"Processing all files for project_id: {project_id}, total files: {len(project_files)}"
        )
        project_files_ids = {
            record.asset_id: record.asset_name for record in project_files
        }
        logger.info(
            f"Processing all files for project_id: {project_id}, total project_files_ids: {project_files_ids}"
        )
    if not project_files_ids or len(project_files_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.NO_FILES_ERROR.value},
        )

    # reset chunks if needed
    if do_reset == 1:
        # Delete the associated vectors collection
        collection_name = nlp_controller.create_collection_name(project_id=project_id)
        # logger.info(f"Deleting collection: {collection_name}")
        _ = await request.app.vector_db_client.delete_collection(
            collection_name=collection_name
        )

        # Delete the associated chunks
        _ = await chunk_db_controller.delete_chunks_by_project_id(project_id=project_id)

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
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": ResponseMessageEnums.PROCESSING_SUCCESS.value,
                "inserted_records": no_record,
                "processed_files": no_files,
            },
        )
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnums.PROCESSING_FAILED.value},
        )

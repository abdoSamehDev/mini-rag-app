import os
from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import aiofiles
from controllers import (
    DataController,
    ProjectController,
    ProcessController,
    ProjectDBController,
    AssetDBController,
)
from helpers import get_settings, Settings, get_logger
from models import (
    ResponseMessageEnums,
    PgAsset as Asset,
    AssetTypeEnums,
)
from .schemes import ProcessRequest
from tasks import process_project_files, process_and_push_workflow

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

    task = process_project_files.delay(
        project_id=project_id,
        file_id=file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        do_reset=do_reset,
    )

    return JSONResponse(
        content={
            "message": ResponseMessageEnums.PROCESSING_SUCCESS.value,
            "task_id": task.id,
        },
    )


@data_router.post("/process-and-push/{project_id}")
async def process_and_push_endpoint(project_id: int, process_request: ProcessRequest):
    # setup request and controllers
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    workflow_task = process_and_push_workflow.delay(
        project_id=project_id,
        file_id=file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        do_reset=do_reset,
    )

    return JSONResponse(
        content={
            "message": ResponseMessageEnums.PROCESS_AND_PUSH_WORKFLOW_READY.value,
            "workflow_task_id": workflow_task.id,
        },
    )

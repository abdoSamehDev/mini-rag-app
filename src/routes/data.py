from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import aiofiles
from controllers import DataController, ProjectController, ProcessController
from helpers import get_settings, Settings
from models import ResponseMessage
from .schemes import ProcessRequest

import logging

data_router = APIRouter(prefix="/api/v1/data", tags=["api_v1", "data"])

logger = logging.getLogger("uvicorn.error")


def get_data_controller():
    return DataController()


def get_project_controller():
    return ProjectController()


def get_process_controller(project_id: str):
    return ProcessController(project_id=project_id)


@data_router.post("/upload/{project_id}")
async def upload_file(
    project_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
    data_controller: DataController = Depends(get_data_controller),
):
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
            content={"message": ResponseMessage.FILE_UPLOAD_FAILED.value},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": ResponseMessage.FILE_UPLOAD_SUCCESS.value,
            "file_id": file_id,
        },
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(
    project_id: str,
    process_request: ProcessRequest,
):
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size

    process_controller = get_process_controller(project_id=project_id)
    try:
        file_content = process_controller.get_file_content(file_id=file_id)

        file_chunks = process_controller.process_file_content(
            chunk_size=chunk_size, overlap_size=overlap_size, file_content=file_content
        )

        if file_chunks is None or len(file_chunks) == 0:
            JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": ResponseMessage.PROCESSING_FAILED.value},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": ResponseMessage.PROCESSING_SUCCESS.value,
                "chunks": jsonable_encoder(file_chunks),
            },
        )
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessage.PROCESSING_FAILED.value},
        )

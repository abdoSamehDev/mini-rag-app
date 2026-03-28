from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
import aiofiles
from controllers import DataController, ProjectController
from helpers import get_settings, Settings
from models import ResponseMessage

import logging

data_router = APIRouter(prefix="/api/v1/data", tags=["api_v1", "data"])

logger = logging.getLogger()


def get_data_controller():
    return DataController()


def get_project_controller():
    return ProjectController()


@data_router.post("/upload/{project_id}")
async def upload_file(
    project_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
    data_controller: DataController = Depends(get_data_controller),
):
    logger.info(
        f"Received file upload request for project_id: {project_id}, file_name: {file.filename}"
    )
    # validate the file
    is_valid, message = data_controller.validate_uplaoded_file(file=file)
    logger.info(f"File validation result: {is_valid}, message: {message}")

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


@data_router.get("/test")
async def test_endpoint():
    return {"message": "Test endpoint is working!"}

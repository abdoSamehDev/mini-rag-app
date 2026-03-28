from fastapi import APIRouter
from helpers import get_settings

base_router = APIRouter(prefix="/api/v1", tags=["api_v1"])

app_settings = get_settings()


@base_router.get("/")
async def welcoome():
    app_name = app_settings.APP_NAME
    app_version = app_settings.APP_VERSION
    return {"message": f"Welcome to {app_name} version {app_version}!"}

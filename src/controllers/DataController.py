from .BaseController import BaseController
from .ProjectController import ProjectController
from fastapi import UploadFile
from models import ResponseMessage
import re
import os


class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576  # convert MB to bytes

    def get_clean_file_name(self, orig_file_name: str):
        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r"[^\w.]", "", orig_file_name.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name

    def validate_uplaoded_file(self, file: UploadFile):

        if file and file.size is not None:
            if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
                return False, ResponseMessage.FILE_TYPE_NOT_SUPPORTED.value

            if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
                return False, ResponseMessage.FILE_SIZE_EXCEEDED.value

            return True, ResponseMessage.FILE_UPLOAD_SUCCESS.value
        else:
            return False, ResponseMessage.FILE_NOT_EXIST.value

    def generate_unique_file_path(self, orignal_file_name: str, project_id: str):
        random_key = self.generate_random_string()

        project_path = ProjectController().get_project_path(project_id=project_id)
        clean_file_name = self.get_clean_file_name(orig_file_name=orignal_file_name)

        new_file_id = f"{random_key}_{clean_file_name}"

        new_file_path = os.path.join(project_path, new_file_id)

        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_id = f"{random_key}_{clean_file_name}"
            new_file_path = os.path.join(project_path, new_file_id)

        return new_file_path, new_file_id

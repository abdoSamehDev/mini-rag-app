from helpers import get_settings
import os
import random
import string


class BaseController:
    def __init__(self):
        self.app_settings = get_settings()

        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.files_dir = os.path.join(self.base_dir, "assets/files")

        self.vector_db_dir = os.path.join(self.base_dir, "assets/database")

    def generate_random_string(self, length: int = 12):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def get_vector_db_path(self, db_name: str):
        vector_db_path = os.path.join(self.vector_db_dir, db_name)

        if not os.path.exists(self.vector_db_path):
            os.makedirs(self.vector_db_path)
        return vector_db_path

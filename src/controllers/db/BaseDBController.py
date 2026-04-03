from helpers import get_settings


class BaseDBController:
    def __init__(self, db_client: object):
        self.app_settings = get_settings()
        self.db_client = db_client

from .BaseDBController import BaseDBController
from models import DataBaseEnums


class AssetDBController(BaseDBController):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnums.ASSETS_COLLECTION.value]

from controllers import BaseController
from .providers import QdrandDBProvider
from .VectorDBEnums import VectorDBProviderEnums


class VectorDBProviderFactory:
    def __init__(self, config: dict):
        self.config = config
        self.base_controller = BaseController()

    def create(self, provider: str):
        if provider == VectorDBProviderEnums.QDRANT.value:
            db_path = self.base_controller.get_vector_db_path(
                db_name=self.config.VECTOR_DB_PATH
            )

            return QdrandDBProvider(
                db_path=db_path, distance_method=self.config.VECTOR_DB_DISTANCE_METHOD
            )
        return None

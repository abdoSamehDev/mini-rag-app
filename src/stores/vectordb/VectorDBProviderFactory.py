from controllers import BaseController
from .providers import QdrandDBProvider, PGVectorProvider
from .VectorDBEnums import VectorDBProviderEnums
from sqlalchemy.orm import sessionmaker


class VectorDBProviderFactory:
    def __init__(self, config: dict, db_client: sessionmaker = None):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create(self, provider: str):
        if provider == VectorDBProviderEnums.QDRANT.value:
            quadrant_db_client = self.base_controller.get_vector_db_path(
                db_name=self.config.VECTOR_DB_PATH
            )

            return QdrandDBProvider(
                db_client=quadrant_db_client,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
                index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
            )

        if provider == VectorDBProviderEnums.PGVECTOR.value:
            return PGVectorProvider(
                db_client=self.db_client,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
                index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD,
            )

        return None

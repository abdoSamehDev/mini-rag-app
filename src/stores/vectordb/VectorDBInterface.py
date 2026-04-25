from abc import ABC, abstractmethod
# from qdrant_client import models
# from models import RetrievedDocument


class VectorDBInterface(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def is_collection_exists(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def list_all_collections(self) -> list:
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False,
    ) -> bool:
        pass

    @abstractmethod
    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: dict,
        record_id: str = None,
    ) -> bool | None:
        pass

    @abstractmethod
    def insert_many(
        self,
        collection_name: str,
        texts: list[str],
        vectors: list,
        metadatas: list[dict] = None,
        record_ids: list[str] = None,
        batch_size: int = 50,
    ) -> bool | None:
        pass

    @abstractmethod
    def search_by_vector(
        self, collection_name: str, vector: list, limit: int = 5
    ) -> list | None:
        pass

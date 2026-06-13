from ...vectordb import VectorDBInterface, DistanceMethodEnums
from qdrant_client import QdrantClient, models
from models import RetrievedDocument
from helpers import get_logger


class QdrandDBProvider(VectorDBInterface):
    def __init__(
        self,
        db_client,
        default_vector_size: int = 786,
        distance_method: str = None,
        index_threshold: int = 100,
    ):
        self.client = None
        self.db_client = db_client
        self.distance_method = None
        self.index_threshold = index_threshold
        self.default_vector_size = default_vector_size

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE
        elif self.distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = get_logger()

    async def connect(self):
        self.client = QdrantClient(path=self.db_client)

    async def disconnect(self):
        self.client = None

    async def is_collection_exists(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)

    async def list_all_collections(self) -> list:
        return self.client.get_collections()

    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)

    async def delete_collection(self, collection_name: str) -> bool:
        self.logger.info(f"Deleting collection {collection_name} from QdrantDB")
        return self.client.delete_collection(collection_name=collection_name)

    async def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False,
    ) -> bool:
        if do_reset:
            self.client.delete_collection(collection_name=collection_name)
        if not self.is_collection_exists(collection_name):
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=embedding_size, distance=self.distance_method
                    ),
                )
            except Exception as e:
                self.logger.error(f"Error creating collection {collection_name}: {e}")
                return False
        return True

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: dict,
        record_id: str = None,
    ) -> bool | None:
        if not self.is_collection_exists(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return None

        try:
            points = [
                models.PointStruct(
                    id=record_id,
                    vector=vector,
                    payload={"text": text, "metadata": metadata},
                )
            ]
            operation_info = self.client.upsert(
                collection_name=collection_name, points=points, wait=True
            )
            self.logger.info(
                f"Inserted point with id {record_id} into collection {collection_name}. Operation info: {operation_info}"
            )
        except Exception as e:
            self.logger.error(
                f"Error inserting point into collection {collection_name}: {e}"
            )
            return False
        return True

    async def insert_many(
        self,
        collection_name: str,
        texts: list[str],
        vectors: list,
        metadatas: list[dict] = None,
        record_ids: list[str] = None,
        batch_size: int = 50,
    ) -> bool | None:
        if not self.is_collection_exists(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return None
        if metadatas is None:
            metadatas = [None] * len(texts)
        if record_ids is None:
            record_ids = list(range(0, len(texts)))
        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size
            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            batch_record_ids = record_ids[i:batch_end]

            batch_points = [
                models.PointStruct(
                    id=batch_record_ids[x],
                    vector=batch_vectors[x],
                    payload={"text": batch_texts[x], "metadata": batch_metadatas[x]},
                )
                for x in range(len(batch_texts))
            ]
            try:
                opertaion_info = self.client.upsert(
                    collection_name=collection_name,
                    wait=True,
                    points=batch_points,
                )
                self.logger.info(
                    f"Inserted batch of points into collection {collection_name}. Operation info: {opertaion_info}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error inserting batch of points into collection {collection_name}: {e}"
                )
                return False
        return True

    async def search_by_vector(
        self, collection_name: str, vector: list, limit: int = 5
    ) -> list | None:
        if not self.is_collection_exists(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return None

        search_result = []
        try:
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=limit,
            ).points
            if not search_result or len(search_result) == 0:
                self.logger.error(
                    f"Error searching for vector in collection {collection_name}"
                )
                return None
        except Exception as e:
            self.logger.error(
                f"Error searching for vector in collection {collection_name}: {e}"
            )
            return None
        return [
            RetrievedDocument(**{"score": result.score, "text": result.payload["text"]})
            for result in search_result
        ]

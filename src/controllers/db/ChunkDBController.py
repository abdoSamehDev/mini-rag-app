from .BaseDBController import BaseDBController
from models import DataBaseEnums, Chunk
from bson.objectid import ObjectId
from pymongo import InsertOne


class ChunkDBController(BaseDBController):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnums.CHUNKS_COLLECTION.value]

    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnums.CHUNKS_COLLECTION.value not in all_collections:
            self.collection = self.db_client[DataBaseEnums.CHUNKS_COLLECTION.value]
            indexes = Chunk.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"],
                )

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_collection()
        return instance

    async def create_chunk(self, chunk: Chunk) -> Chunk:
        result = await self.db_client.insert_one(
            chunk.model_dumb(by_alias=True, exclude_unset=True)
        )
        chunk.id = result.inserted_id
        return chunk

    async def get_chunk_by_id(self, chunk_id: str) -> Chunk | None:
        record = await self.db_client.find_one({"_id": ObjectId(chunk_id)})
        if record:
            return Chunk(**record)
        return None

    async def insert_many_chunks(
        self, chunks: list[Chunk], batch_size: int = 100
    ) -> int | None:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            operations = [
                InsertOne(chunk.model_dump(by_alias=True, exclude_unset=True))
                for chunk in batch
            ]
            await self.collection.bulk_write(operations)
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: str) -> int:
        result = await self.collection.delete_many(
            {"chunk_project_id": ObjectId(project_id)}
        )
        return result.deleted_count

    async def get_project_chunks(
        self, project_id: str, page_no: int = 1, page_size: int = 50
    ) -> list[Chunk]:
        skip = (page_no - 1) * page_size
        records = (
            await self.collection.find({"chunk_project_id": project_id})
            .skip(skip)
            .limit(page_size)
            .to_list(length=None)
        )

        return [Chunk(**record) for record in records]

from .BaseDBController import BaseDBController

# from models import DataBaseEnums, Chunk  # for Mongo
from models import PgChunk

# from bson.objectid import ObjectId
# from pymongo import InsertOne
from sqlalchemy.future import select
from sqlalchemy import func, delete


class ChunkDBController(BaseDBController):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        # self.collection = self.db_client[DataBaseEnums.CHUNKS_COLLECTION.value]  # for Mongo
        self.db_client = db_client  # for postgres

    # # for Mongo
    # async def init_collection(self):
    #     all_collections = await self.db_client.list_collection_names()
    #     if DataBaseEnums.CHUNKS_COLLECTION.value not in all_collections:
    #         self.collection = self.db_client[DataBaseEnums.CHUNKS_COLLECTION.value]
    #         indexes = Chunk.get_indexes()
    #         for index in indexes:
    #             await self.collection.create_index(
    #                 index["key"],
    #                 name=index["name"],
    #                 unique=index["unique"],
    #             )

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        # await instance.init_collection()  # for Mongo
        return instance

    async def create_chunk(self, chunk: PgChunk) -> PgChunk:

        # # for Mongo
        # result = await self.db_client.insert_one(
        #     chunk.model_dumb(by_alias=True, exclude_unset=True)
        # )
        # chunk.id = result.inserted_id
        # return chunk

        ##for Postgres
        async with self.db_client() as session:
            async with session.begin():
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
        return chunk

    async def get_chunk_by_id(self, chunk_id: str) -> PgChunk | None:

        # # for Mongo
        # record = await self.db_client.find_one({"_id": ObjectId(chunk_id)})
        # if record:
        #     return Chunk(**record)
        # return None

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                query = select(PgChunk).where(PgChunk.chunk_id == chunk_id)
                chunk = await session.execute(query).scalar_one_or_none()
            return chunk

    async def insert_many_chunks(
        self, chunks: list[PgChunk], batch_size: int = 100
    ) -> int | None:
        # # for Mongo
        # for i in range(0, len(chunks), batch_size):
        #     batch = chunks[i : i + batch_size]
        #     operations = [
        #         InsertOne(chunk.model_dump(by_alias=True, exclude_unset=True))
        #         for chunk in batch
        #     ]
        #     await self.collection.bulk_write(operations)
        # return len(chunks)

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i : i + batch_size]
                    session.add_all(batch)
                await session.commit()
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: str) -> int:

        # # for Mongo
        # result = await self.collection.delete_many(
        #     {"chunk_project_id": ObjectId(project_id)}
        # )
        # return result.deleted_count

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                query = delete(PgChunk).where(PgChunk.chunk_project_id == project_id)
                result = await session.execute(query)
                await session.commit()
        return result.rowcount

    async def get_project_chunks(
        self, project_id: str, page_no: int = 1, page_size: int = 50
    ) -> list[PgChunk]:
        # # for Mongo
        # skip = (page_no - 1) * page_size
        # records = (
        #     await self.collection.find({"chunk_project_id": project_id})
        #     .skip(skip)
        #     .limit(page_size)
        #     .to_list(length=None)
        # )

        # return [Chunk(**record) for record in records]

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                query = (
                    select(PgChunk)
                    .where(PgChunk.chunk_project_id == project_id)
                    .offset((page_no - 1) * page_size)
                    .limit(page_size)
                )
                records = await session.execute(query)
                chunks = records.scalars().all()
            return chunks

    async def get_total_chunks_count(self, project_id: str) -> int:
        async with self.db_client() as session:
            async with session.begin():
                count_sql = select(func.count(PgChunk.chunk_id)).where(
                    PgChunk.chunk_project_id == project_id
                )
                recs_count = await session.execute(count_sql)
                chunks_count = recs_count.scalar()
        return chunks_count

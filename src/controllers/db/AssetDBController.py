from .BaseDBController import BaseDBController

# from models import DataBaseEnums, Asset
from models import PgAsset

# from bson.objectid import ObjectId #for Mongo
from typing import Optional
from sqlalchemy import select


class AssetDBController(BaseDBController):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        # self.collection = self.db_client[DataBaseEnums.ASSETS_COLLECTION.value]  # for Mongo
        self.db_client = db_client  # for postgres

    # #for Mongo
    # async def init_collection(self):
    #     all_collections = await self.db_client.list_collection_names()
    #     if DataBaseEnums.ASSETS_COLLECTION.value not in all_collections:
    #         self.collection = self.db_client[DataBaseEnums.ASSETS_COLLECTION.value]
    #         indexes = Asset.get_indexes()
    #         for index in indexes:
    #             await self.collection.create_index(
    #                 index["key"],
    #                 name=index["name"],
    #                 unique=index["unique"],
    #             )

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        # await instance.init_collection() #for Mongo
        return instance

    async def create_asset(self, asset: PgAsset) -> PgAsset:

        # # for Mongo
        # result = await self.collection.insert_one(
        #     asset.model_dump(by_alias=True, exclude_unset=True)
        # )
        # asset.id = result.inserted_id
        # return asset

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)
        return asset

    async def get_all_project_assets(
        self, asset_project_id: str, asset_type: str
    ) -> Optional[list[PgAsset]]:

        # # for Mongo
        # records = await self.collection.find(
        #     {
        #         "asset_project_id": ObjectId(asset_project_id)
        #         if isinstance(asset_project_id, str)
        #         else asset_project_id,
        #         "asset_type": asset_type,
        #     }
        # ).to_list(length=None)
        # if records:
        #     return [Asset(**record) for record in records]
        # return None

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                query = select(PgAsset).where(
                    PgAsset.asset_project_id == asset_project_id,
                    PgAsset.asset_type == asset_type,
                )
                assets = await session.execute(query).scalars().all()
        return assets

    async def get_asset_record(
        self, asset_project_id: str, asset_name: str
    ) -> Optional[PgAsset]:

        # # for Mongo
        # record = await self.collection.find_one(
        #     {
        #         "asset_project_id": ObjectId(asset_project_id)
        #         if isinstance(asset_project_id, str)
        #         else asset_project_id,
        #         "asset_name": asset_name,
        #     }
        # )
        # if record:
        #     return Asset(**record)
        # return None

        # for Postgres
        async with self.db_client() as session:
            async with session.begin():
                query = select(PgAsset).where(
                    PgAsset.asset_project_id == asset_project_id,
                    PgAsset.asset_name == asset_name,
                )
                record = await session.execute(query)
                asset = record.scalar_one_or_none()
        return asset

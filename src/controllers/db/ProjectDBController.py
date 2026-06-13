# from bson.objectid import ObjectId
from .BaseDBController import BaseDBController
from models import PgProject
from sqlalchemy import func
from sqlalchemy.future import select


class ProjectDBController(BaseDBController):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        # self.collection = self.db_client[DataBaseEnums.PROJECTS_COLLECTION.value] # for Mongo
        self.db_client = db_client  # for postgres

    # for Mongo
    # async def init_collection(self):
    #     all_collections = await self.db_client.list_collection_names()
    #     if DataBaseEnums.PROJECTS_COLLECTION.value not in all_collections:
    #         self.collection = self.db_client[DataBaseEnums.PROJECTS_COLLECTION.value]
    #         indexes = Project.get_indexes()
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

    async def create_project(self, project: PgProject) -> PgProject:
        # for postgres
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)
        return project

        # for Mongo
        # result = await self.collection.insert_one(
        #     project.model_dump(by_alias=True, exclude_unset=True)
        # )
        # project.id = result.inserted_id
        # return project

    async def get_project_or_create_one(self, project_id: int) -> PgProject:

        # for Mongo
        # record = await self.collection.find_one({"project_id": project_id})
        # if record is None:
        #     # create new project
        #     project = Project(project_id=project_id)
        #     project = await self.create_project(project)
        #     return project
        # else:
        #     return Project(**record)

        # for postgres
        async with self.db_client() as session:
            async with session.begin():
                query = select(PgProject).where(PgProject.project_id == project_id)
                record = await session.execute(query)
                project = record.scalar_one_or_none()
                if project is None:
                    project_rec = PgProject(project_id=project_id)
                    project = await self.create_project(project=project_rec)
                    return project
                else:
                    return project

    async def get_all_projects(
        self, page: int = 1, page_size: int = 10
    ) -> tuple[list[PgProject], int]:

        # # for Mongo
        # # count total docs in the collection
        # total_docs = await self.collection.count_documents({})

        # # calc total pages
        # total_pages = total_docs // page_size
        # if total_docs % page_size != 0:
        #     total_pages += 1

        # skip = (page - 1) * page_size

        # cursor = await self.collection.find().skip(skip).limit(page_size)
        # projects = []
        # async for doc in cursor:
        #     projects.append(Project(**doc))
        # return projects, total_pages

        # for postgres
        async with self.db_client() as session:
            async with session.begin():
                total_docs = await session.execute(
                    select(func.count(PgProject.project_id))
                ).scalar_one()
                total_pages = total_docs // page_size
                if total_docs % page_size > 0:
                    total_pages += 1
                query = (
                    select(PgProject).offset((page - 1) * page_size).limit(page_size)
                )
                projects = await session.execute(query).scalars().all()

            return projects, total_pages

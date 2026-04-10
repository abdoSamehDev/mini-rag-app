from typing import Any

from .BaseController import BaseController
from models import Project, Chunk, RetrievedDocument
from stores import DocTypeEnums

import json


class NLPController(BaseController):
    def __init__(
        self, vectordb_client, generation_client, embedding_client, template_parser
    ):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser

    def create_collection_name(self, project_id: str) -> str:
        return f"collection_{project_id}".strip()

    def reset_vector_db_collection(self, project: Project) -> bool:
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)

    def get_vector_db_collection_info(self, project: Project) -> Any:
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = self.vectordb_client.get_collection_info(
            collection_name=collection_name
        )

        # when the returned type is some complex object that can't be JSONed on its own, this way "might" help
        return json.loads(json.dumps(collection_info, default=lambda x: x.__dict__))
        # 1. json.dumbs() turn all objs into JSON string, and if there is some objs can't be JSONed
        #   use __dict__
        # __dict__ is a method that most lobraries creators use as native in their library to convert the obj inot a dict
        # 2. the string that comes out of json.dumbs(), json.loads() turns it into a dict

    def index_into_vector_db(
        self,
        project: Project,
        chunks: list[Chunk],
        chunk_ids: list[int],
        do_reset: int = 0,
    ) -> bool | None:
        # step1: create collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items (chunks into points)
        texts = [c.chunk_text for c in chunks]
        metadatas = [c.chunk_metadata for c in chunks]
        vectors = [
            self.embedding_client.embed_text(
                text=text, doc_type=DocTypeEnums.DOCUMENT.value
            )
            for text in texts
        ]

        # step3: create collection if not exist
        _ = self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        results = self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            vectors=vectors,
            metadatas=metadatas,
            record_ids=chunk_ids,
        )
        return results

    def search_vector_db_collection(
        self, project: Project, text: str, limit: int = 10
    ) -> list[RetrievedDocument] | None:
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: get text embedding vector (doc_type = query)
        vector = self.embedding_client.embed_text(
            text=text, doc_type=DocTypeEnums.QUERY.value
        )
        # step3: validate
        if not vector or len(vector) == 0:
            return None

        # step4: do semantic search
        results = self.vectordb_client.search_by_vector(
            collection_name=collection_name, vector=vector, limit=limit
        )
        if not results:
            return None
        return results

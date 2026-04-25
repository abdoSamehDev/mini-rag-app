from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader

# from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import ProcessingEnums
from dataclasses import dataclass


@dataclass
class DocunmentChunk:
    page_content: str
    metadata: dict


class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str):
        file_extension = os.path.splitext(file_id)[-1]
        return file_extension

    def get_file_loader(self, file_id: str):
        file_extension = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if file_extension == ProcessingEnums.PDF.value:
            return PyMuPDFLoader(file_path=file_path)
        if file_extension == ProcessingEnums.TXT.value:
            return TextLoader(file_path=file_path, encoding="utf-8")
        return None

    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id=file_id)
        return loader.load()

    def process_file_content(
        self,
        file_content: list[str],
        chunk_size: int = 100,
        overlap_size: int = 20,
    ):
        # text_splitter = RecursiveCharacterTextSplitter(
        #     chunk_size=chunk_size,
        #     chunk_overlap=overlap_size,
        #     length_function=len,
        # )

        file_content_text = [rec.page_content for rec in file_content]
        file_content_metadata = [rec.metadata for rec in file_content]

        # chunks = text_splitter.create_documents(
        #     file_content_text,
        #     metadatas=file_content_metadata,
        # )

        chunks = self.process_simpler_splitter(
            texts=file_content_text,
            metadatas=file_content_metadata,
            chunk_size=chunk_size,
        )
        return chunks

    def process_simpler_splitter(
        self,
        texts: list[str],
        metadatas: list[dict],
        chunk_size: int,
        splitter_tag: str = "\n",
    ):

        full_text = " ".join(texts)

        # split by \n
        lines = [
            doc.strip() for doc in full_text.split(splitter_tag) if len(doc.strip()) > 1
        ]
        chunks = []
        current_chunk = ""
        for line in lines:
            current_chunk += line + splitter_tag
            if len(current_chunk) >= chunk_size:
                chunks.append(
                    DocunmentChunk(page_content=current_chunk.strip(), metadata={})
                )
                current_chunk = ""
        if len(current_chunk) >= 0:
            chunks.append(
                DocunmentChunk(page_content=current_chunk.strip(), metadata={})
            )
        return chunks

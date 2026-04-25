from enum import Enum


class VectorDBProviderEnums(Enum):
    QDRANT = "QDRANT"
    PGVECTOR = "PGVECTOR"


class DistanceMethodEnums(Enum):
    COSINE = "COSINE"
    DOT = "DOT"


class PgVectorTableSchemeEnums(Enum):
    ID = "id"
    TEXT = "text"
    VECTOR = "vector"
    CHUNK_ID = "chunk_id"
    METADATA = "metadata"
    _PREFIX = (
        "pgvector"  # prefix for pgvector columns names to help searching pgvector data
    )


class PgVectorDistanceMethod(Enum):
    COSINE = "vector_cosine_ops"
    DOT = "vector_12_ops"


class PgVectorIndexTypeEnums(Enum):
    HNSW = "hnsw"
    IVFFLAT = "ivfflat"

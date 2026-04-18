from enum import Enum


class VectorDBProviderEnums(Enum):
    QDRANT = "QDRANT"


class DistanceMethodEnums(Enum):
    COSINE = "COSINE"
    DOT = "DOT"

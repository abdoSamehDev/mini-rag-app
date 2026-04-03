from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson.objectid import ObjectId


class Chunk(BaseModel):
    # this is the eq in the PydanticV2 same functionality as
    # PydanticV1's Config class with arbitrary_types_allowed = True
    # Class Config:
    #    arbitrary_types_allowed = True
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[ObjectId] = Field(None, alias="_id")
    chunk_project_id: ObjectId
    chunk_asset_id: ObjectId
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [
                    ("chunk_project_id", 1),
                ],
                "name": "chunk_project_id_index_1",
                "unique": False,
            },
            {
                "key": [
                    ("chunk_asset_id", 1),
                ],
                "name": "chunk_project_id_index_1",
                "unique": False,
            },
        ]

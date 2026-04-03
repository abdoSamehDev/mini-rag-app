from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson.objectid import ObjectId


class DataChunkDBScheme(BaseModel):
    # this is the eq in the PydanticV2 same functionality as
    # PydanticV1's Config class with arbitrary_types_allowed = True
    # Class Config:
    #    arbitrary_types_allowed = True
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[ObjectId] = Field(None, alias="_id")
    data_chunk_project_id: ObjectId
    data_chunk_asset_id: ObjectId
    data_chunk_text: str = Field(..., min_length=1)
    data_chunk_metadata: dict
    data_chunk_order: int = Field(..., gt=0)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson.objectid import ObjectId
from datetime import datetime, timezone


class AssetDBScheme(BaseModel):
    # this is the eq in the PydanticV2 same functionality as
    # PydanticV1's Config class with arbitrary_types_allowed = True
    # Class Config:
    #    arbitrary_types_allowed = True
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[ObjectId] = Field(None, alias="_id")
    asset_project_id: ObjectId
    asset_type: str = Field(..., min_length=1)
    asset_name: str = Field(..., min_length=1)
    asset_size: Optional[int] = Field(ge=0, default=None)
    asset_config: Optional[dict] = Field(default=None)
    asset_pushed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [
                    ("asset_project_id", 1),
                    ("asset_name", 1),
                ],
                "name": "asset_project_id_name_index_1",
                "unique": True,
            }
        ]

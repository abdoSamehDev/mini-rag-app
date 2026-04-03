from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from bson.objectid import ObjectId


class Project(BaseModel):
    # this is the eq in the PydanticV2 same functionality as
    # PydanticV1's Config class with arbitrary_types_allowed = True
    # Class Config:
    #    arbitrary_types_allowed = True
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[ObjectId] = Field(None, alias="_id")
    project_id: ObjectId

    @field_validator("project_id")
    def validate_project_id(cls, v):
        if not v.isalnum():
            raise ValueError("project_id must be alphanumeric")
        return v

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [
                    ("project_id", 1),
                ],
                "name": "project_id_index_1",
                "unique": True,
            },
        ]

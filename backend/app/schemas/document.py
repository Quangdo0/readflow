from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class DocumentUpdate(BaseModel):
    version: int = Field(ge=1)
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    content: str | None = Field(
        default=None,
        min_length=1,
    )


class DocumentRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    title: str
    content: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


AnimalSex = Literal["male", "female", "mixed"]
AnimalGroupStatus = Literal["active", "closed"]


class AnimalGroupCreate(BaseModel):
    farm_id: UUID
    species_id: int = Field(ge=1, le=32767)
    breed_id: int | None = Field(default=None, ge=1)
    group_name: str = Field(min_length=1)
    sex: AnimalSex = "mixed"
    date_established: date | None = None
    initial_head_count: int = Field(gt=0)
    current_head_count: int = Field(ge=0)
    status: AnimalGroupStatus = "active"
    remarks: str | None = None

    @field_validator("group_name")
    @classmethod
    def validate_group_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Group name cannot be empty")

        return value

    @field_validator("remarks")
    @classmethod
    def clean_remarks(cls, value: str | None):
        if value is not None:
            value = value.strip() or None
        return value


class AnimalGroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    species_id: int | None = Field(default=None, ge=1, le=32767)
    breed_id: int | None = Field(default=None, ge=1)
    group_name: str | None = Field(default=None, min_length=1)
    sex: AnimalSex | None = None
    date_established: date | None = None
    initial_head_count: int | None = Field(default=None, gt=0)
    current_head_count: int | None = Field(default=None, ge=0)
    status: AnimalGroupStatus | None = None
    remarks: str | None = None

    @field_validator("group_name")
    @classmethod
    def validate_group_name(cls, value: str | None):
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError("Group name cannot be empty")

        return value

    @field_validator("remarks")
    @classmethod
    def clean_remarks(cls, value: str | None):
        if value is not None:
            value = value.strip() or None
        return value


class AnimalGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    animal_group_id: UUID
    farm_id: UUID
    species_id: int
    breed_id: int | None
    group_name: str
    sex: AnimalSex
    date_established: date
    initial_head_count: int
    current_head_count: int
    status: AnimalGroupStatus
    remarks: str | None
    created_at: datetime
    updated_at: datetime

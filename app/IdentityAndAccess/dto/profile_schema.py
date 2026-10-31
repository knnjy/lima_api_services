
from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1)
    middle_name: str | None = None
    last_name: str = Field(min_length=1)
    suffix: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    profile_photo_path: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    @field_validator("middle_name", "suffix", "gender",
                     "profile_photo_path")
    @classmethod
    def clean_optional_fields(cls, value: str | None):
        if value is not None:
            value = value.strip()
            return value or None

        return value


class ProfileCreate(ProfileCreateRequest):
    user_id: UUID


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1)
    middle_name: str | None = None
    last_name: str | None = Field(default=None, min_length=1)
    suffix: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    profile_photo_path: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    @field_validator("middle_name", "suffix", "gender",
                     "profile_photo_path")
    @classmethod
    def clean_optional_fields(cls, value: str | None):
        if value is not None:
            value = value.strip()
            return value or None

        return value

    @model_validator(mode="after")
    def validate_update_fields(self) -> "ProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")

        for field_name in ("first_name", "last_name"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")

        return self


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    first_name: str
    middle_name: str | None
    last_name: str
    suffix: str | None
    birth_date: date | None
    gender: str | None
    profile_photo_path: str | None
    created_at: datetime
    updated_at: datetime


from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.IdentityAndAccess.dto.profile_schema import ProfileResponse


class UserPreferencesCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_code: str = Field(default="fil", min_length=2)
    timezone: str = Field(default="Asia/Manila", min_length=1)

    @field_validator("language_code", "timezone")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value


class UserPreferencesCreate(UserPreferencesCreateRequest):
    user_id: UUID


class UserPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_code: str | None = Field(default=None, min_length=2)
    timezone: str | None = Field(default=None, min_length=1)

    @field_validator("language_code", "timezone")
    @classmethod
    def validate_non_empty(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_update_fields(self) -> "UserPreferencesUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")

        for field_name in ("language_code", "timezone"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")

        return self


class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    language_code: str
    timezone: str
    updated_at: datetime


class UserViewResponse(BaseModel):
    profile: ProfileResponse
    user_preferences: UserPreferencesResponse


from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.common.dto.page_meta_dto import PageMeta


class FarmCreate(BaseModel):
    farm_name: str = Field(min_length=1)
    created_by: UUID | None = None
    province: str = Field(min_length=1)
    city_municipality: str = Field(min_length=1)
    address_line: str | None = None
    is_active: bool = True

    @field_validator(
        "farm_name", "province", "city_municipality"
    )
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty or whitespace")

        return value


class FarmUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farm_name: str | None = Field(default=None, min_length=1)
    province: str | None = Field(default=None, min_length=1)
    city_municipality: str | None = Field(
        default=None, min_length=1
    )
    address_line: str | None = None
    is_active: bool | None = None

    @field_validator(
        "farm_name", "province", "city_municipality"
    )
    @classmethod
    def validate_non_empty(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty or whitespace")

        return value

    @model_validator(mode="after")
    def validate_required_fields(self) -> "FarmUpdate":
        for field_name in ("farm_name", "province", "city_municipality"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    farm_id: UUID
    farm_name: str
    created_by: UUID | None
    province: str
    city_municipality: str
    address_line: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class FarmLocation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    province: str
    city_municipality: str
    address_line: str | None = None

class FarmMembershipRole(BaseModel):
    """The signed-in user's membership and role in this farm."""
    model_config = ConfigDict(from_attributes=True)

    membership_id: UUID
    role_id: int
    role_name: str

class FarmListItem(BaseModel):
    """One farm card on the Home screen."""
    model_config = ConfigDict(from_attributes=True)

    farm_id: UUID
    farm_name: str
    location: FarmLocation
    role: FarmMembershipRole

class FarmListResponse(BaseModel):
    data: list[FarmListItem]
    meta: PageMeta

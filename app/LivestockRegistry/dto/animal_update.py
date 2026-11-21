
# Request model for updating an animal
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.LivestockRegistry.dto.animal_literal import AnimalSex, AnimalStatus


class AnimalUpdate(BaseModel):
    farm_id: UUID | None = None
    species_id: int | None = Field(default=None, ge=0, le=32767)
    breed_id: int | None = None
    animal_group_id: UUID | None = None
    identifier_number: str | None = None
    name: str | None = None
    sex: AnimalSex | None = None
    birth_date: date | None = None
    current_status: AnimalStatus | None = None
    remarks: str | None = None
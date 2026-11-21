
# Request model for creating an animal
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.LivestockRegistry.dto.animal_literal import AnimalSex, AnimalStatus


class AnimalCreate(BaseModel):
    farm_id: UUID
    species_id: int = Field(ge=0, le=32767)
    breed_id: int | None = None
    animal_group_id: UUID | None = None
    identifier_number: str | None = None
    name: str | None = None
    sex: AnimalSex = "unknown"
    birth_date: date | None = None
    current_status: AnimalStatus = "active"
    remarks: str | None = None
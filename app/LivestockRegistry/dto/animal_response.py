
# Request model for creating an animal
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.LivestockRegistry.dto.animal_literal import AnimalSex, AnimalStatus

class AnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    animal_id: UUID
    farm_id: UUID
    species_id: int
    breed_id: int | None = None
    animal_group_id: UUID | None = None
    identifier_number: str | None = None
    name: str | None = None
    sex: AnimalSex
    birth_date: date | None = None
    current_status: AnimalStatus
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime

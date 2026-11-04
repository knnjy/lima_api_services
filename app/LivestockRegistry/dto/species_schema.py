from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpeciesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    species_id: int
    species_name: str
    created_at: datetime
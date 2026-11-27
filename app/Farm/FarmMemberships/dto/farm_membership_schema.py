
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MembershipStatus = Literal["active", "removed"]


class FarmMembershipCreate(BaseModel):
    user_id: uuid.UUID
    farm_id: uuid.UUID
    role_id: int = Field(ge=-32768, le=32767)
    invitation_id: uuid.UUID | None = None
    status: MembershipStatus = "active"


class FarmMembershipUpdate(BaseModel):
    role_id: int | None = Field(
        default=None, ge=-32768, le=32767
    )
    status: MembershipStatus | None = None
    invitation_id: uuid.UUID | None = None


class FarmMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    farm_id: uuid.UUID
    role_id: int
    invitation_id: uuid.UUID | None
    status: MembershipStatus
    joined_at: datetime
    updated_at: datetime

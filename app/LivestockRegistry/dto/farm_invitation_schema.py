from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


InvitationStatus = Literal[
    "pending",
    "accepted",
    "expired",
    "cancelled",
]
InvitationEmailStatus = Literal["not_requested", "accepted_by_provider"]


class FarmInvitationCreate(BaseModel):
    role_id: int = Field(gt=0)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    expires_at: datetime

    @model_validator(mode="after")
    def validate_contact(self):
        if not self.email and not self.phone:
            raise ValueError("At least an email or phone number is required.")

        if self.email:
            self.email = str(self.email).lower().strip()

        if self.phone:
            self.phone = self.phone.strip()
            if not self.phone:
                self.phone = None

        if not self.email and not self.phone:
            raise ValueError("At least an email or phone number is required.")

        return self


class FarmInvitationAccept(BaseModel):
    invitation_token: str = Field(min_length=1)


class FarmInvitationResponse(BaseModel):
    invitation_id: UUID
    farm_id: UUID
    role_id: int
    invited_by: UUID
    invited_by_email: str | None = None
    email: str | None
    phone: str | None
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None

    # token_hash is deliberately excluded.


class FarmInvitationCreatedResponse(FarmInvitationResponse):
    # Provider acceptance is not a guarantee of inbox delivery.
    invitation_token: str
    email_delivery_status: InvitationEmailStatus = "not_requested"
    email_message_id: str | None = None


class CreatedInvitationResponse(BaseModel):
    invitation_id: UUID
    farm_id: UUID
    role_id: int
    invited_by: UUID
    email: str | None
    phone: str | None
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None
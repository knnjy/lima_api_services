from pydantic import BaseModel


class TokenVerificationResponse(BaseModel):
    valid: bool = True
    user_id: str
    email: str | None = None

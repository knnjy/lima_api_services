from pydantic import BaseModel, Field


class SignInRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class SignInResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int | None = None
    user_id: str
    email: str | None = None


class TokenVerificationResponse(BaseModel):
    valid: bool = True
    user_id: str
    email: str | None = None

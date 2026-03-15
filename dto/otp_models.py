from pydantic import BaseModel, Field


class OtpVerifyRequest(BaseModel):
    access_token: str = Field(
        ...,
        min_length=1,
        description="JWT access-token returned by the MSG91 OTP widget on the client",
    )

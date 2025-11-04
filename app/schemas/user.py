from pydantic import BaseModel, validator, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def password_max_bytes(cls, v: str) -> str:
        """Ensure password does not exceed bcrypt's 72-byte limit when UTF-8 encoded.

        Raise a validation error so API returns a 422 with a clear message.
        """
        if isinstance(v, str):
            b = v.encode("utf-8")
            if len(b) > 72:
                raise ValueError("password too long: must be at most 72 bytes when UTF-8 encoded")
        return v

class UserOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True

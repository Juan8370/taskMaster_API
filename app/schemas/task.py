from pydantic import BaseModel, validator
from typing import Optional

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""

    @validator("title")
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = ""
    user_email: str

    class Config:
        orm_mode = True

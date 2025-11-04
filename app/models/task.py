from sqlalchemy import Column, Integer, String, ForeignKey, Text
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_email = Column(String, ForeignKey("users.email"))

"""SQLModel database models for the DevBrain platform service."""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    github_id: int = Field(unique=True, index=True)
    github_login: str
    github_name: Optional[str] = None
    avatar_url: str = ""
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    instances: list["Instance"] = Relationship(back_populates="user")


class Instance(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    repo: str  # "owner/repo"
    port: int
    status: str = "pending"  # pending | running | stopped | error
    secrets_enc: str = ""  # Fernet-encrypted JSON blob
    created_at: datetime = Field(default_factory=datetime.utcnow)
    container_api_name: str = ""
    container_worker_name: str = ""
    container_redis_name: str = ""
    user: Optional[User] = Relationship(back_populates="instances")

    @property
    def api_url(self) -> str:
        return f"http://localhost:{self.port}"

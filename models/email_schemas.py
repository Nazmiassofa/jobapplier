## models/email_schemas.py

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic import ConfigDict
from typing import Dict, List

class EmailAccountSchema(BaseModel):
    """Email account credentials."""
    id: int
    email: EmailStr
    app_password: str
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class EmailAccountProfile(BaseModel):
    """User profile information."""
    account_id: int
    name: str
    username: str
    gender: str  # 'male' or 'female'
    phone: str

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        v = v.lower()
        if v not in {"male", "female"}:
            raise ValueError('Gender must be "male" or "female"')
        return v

    model_config = ConfigDict(from_attributes=True)


class EmailAccountData(BaseModel):
    """Account data configuration."""
    account_id: int
    blocked_job_position: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "keywords": [],
            "regex_patterns": []
        }
    )
    # Example:
    # {
    #   "keywords": ["guru", "dokter"],
    #   "regex_patterns": [".*medis.*"]
    # }
    

    model_config = ConfigDict(from_attributes=True)


class CompleteAccountInfo(BaseModel):
    """Complete account information for sending email."""
    account: EmailAccountSchema
    profile: EmailAccountProfile
    data: EmailAccountData
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    login: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class SessionContext(BaseModel):
    user_id: int
    login: str
    role: Literal["admin", "operator"]


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    login: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    role: Literal["admin", "operator"] = "operator"


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    new_password: str = Field(..., min_length=8)
    deactivate: bool = False

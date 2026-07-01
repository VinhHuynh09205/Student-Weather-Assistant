import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.]+$", v):
            raise ValueError("Tên đăng nhập chỉ gồm chữ cái, số, dấu gạch dưới (_) và dấu chấm (.)")
        if " " in v:
            raise ValueError("Tên đăng nhập không được chứa khoảng trắng")
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không khớp.")
        return self


class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class UserResponse(UserBase):
    id: UUID
    auth_provider: str
    is_active: bool
    is_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    requires_2fa: bool = False
    temp_token: str | None = None


class TokenData(BaseModel):
    user_id: UUID | None = None


class TwoFactorSetupResponse(BaseModel):
    qr_code_base64: str
    manual_key: str


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class TwoFactorLoginRequest(BaseModel):
    temp_token: str
    code: str = Field(..., min_length=6, max_length=6)

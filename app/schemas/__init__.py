from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignUp(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization: str = ""
    job_title: str = ""


class SignIn(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class EmailIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: str
    organization: str
    job_title: str
    bio: str
    interests: str
    is_verified: bool


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    organization: str | None = None
    job_title: str | None = None
    bio: str | None = None
    interests: str | None = None


class SpeakerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    title: str
    company: str
    bio: str
    featured: bool


class TalkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    track: str
    room: str
    day: int
    starts_at: datetime
    ends_at: datetime
    speakers: list[SpeakerOut]
    saved: bool = False


class SpeakerDetail(SpeakerOut):
    talks: list[TalkOut] = []


class RoleUpdate(BaseModel):
    role: str = Field(pattern="^(attendee|speaker|organizer|admin)$")

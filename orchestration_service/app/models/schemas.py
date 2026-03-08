from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserAdd(BaseModel):
    username: str

class UserUpdateRole(BaseModel):
    role: str

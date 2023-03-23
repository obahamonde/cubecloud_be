from typing import List, Optional, Union, Any, Dict
from datetime import datetime
from src.model.orm import *


class User(FaunaModel):
    """User model."""
    sub: str = Field(...,index=True)
    nickname: Optional[str] = Field(default=None)
    name:Optional[str] = Field(default=None)
    picture: Optional[str] = Field(default=None)
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(),index=True)
    email:Optional[str] = Field(default=None,index=True)
    email_verified:Optional[bool] = Field(default=None,index=True)
 
    def upsert(self, sub:str):
        """Upsert a user."""
        user = User.q()(q.get(q.match(q.index("user_by_sub"), sub)))
        if user:
            user = User(**user["data"])
            return user.dict()
        else:
            self.create()
        return self.dict()
    

class ContainerCreate(BaseModel):
    owner: str = Field(...)
    repo: str = Field(...)
    port: int = Field(default=8080)
    env_vars: List[str] = Field(default=["DOCKER=1"])
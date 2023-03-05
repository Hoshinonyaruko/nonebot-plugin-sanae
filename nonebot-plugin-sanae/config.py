from typing import Set, Optional

from pydantic import BaseModel


class Config(BaseModel):
    sanae_ws: str = None
    sanae_port: str = None

    class Config:
        extra = "ignore"
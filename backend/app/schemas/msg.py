from pydantic import BaseModel

class Msg(BaseModel):
    """Simple message response schema."""
    msg: str

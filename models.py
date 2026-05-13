from pydantic import BaseModel

class UpdateBody(BaseModel):
    venue: str
    entered: int
    exited: int

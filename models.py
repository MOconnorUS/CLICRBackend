from pydantic import BaseModel

class UpdateBody(BaseModel):
    venue: str
    value: int

from pydantic import BaseModel


class PaginationResponse(BaseModel):
    total: int
    limit: int
    offset: int

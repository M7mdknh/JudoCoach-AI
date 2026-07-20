from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=10, max_length=2000)
    require_approval: bool = True


class ResearchResponse(BaseModel):
    status: str
    result: str
    report_id: str
from pydantic import BaseModel

class UserSearchResult(BaseModel):
    total_count: int
    users: list
    page: int

class ProjectSearchResult(BaseModel):
    total_count: int
    projects: list
    page: int

class AISummaryResult(BaseModel):
    ai_summary: str

class PersonaResult(BaseModel):
    persona: str
    icon: str

class RigorResult(BaseModel):
    grade: str
    raw_score: float

class TrendsResult(BaseModel):
    trends: dict

class HealthResult(BaseModel):
    status: str
    github_token: bool
    gemini_key: bool
    groq_key: bool

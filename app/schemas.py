from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr


# ── User ──────────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    username:         str = Field(..., min_length=3, max_length=100)
    email:            EmailStr
    user_role:        Literal["Verwaltung", "Leader", "Mitarbeiter"]
    assigned_project: Optional[str] = None
    department:       Optional[str] = None
    reports_to:       Optional[int] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id:               int
    progress_percent: int
    created_at:       datetime
    class Config:
        from_attributes = True


# ── Task ──────────────────────────────────────────────────────────────────
class TaskBase(BaseModel):
    title:        str = Field(..., min_length=3, max_length=255)
    description:  Optional[str] = None
    task_type:    Literal["Onboarding", "Projekt"]
    project_name: Optional[str] = None
    assigned_to:  int

class TaskCreate(TaskBase):
    assigned_by: Optional[int] = None

class TaskResponse(TaskBase):
    id:           int
    assigned_by:  Optional[int]
    is_completed: bool
    completed_at: Optional[datetime]
    created_at:   datetime
    class Config:
        from_attributes = True


# ── Leader ────────────────────────────────────────────────────────────────
class TeamMemberProgress(BaseModel):
    id:               int
    username:         str
    email:            str
    progress_percent: int
    department:       Optional[str] = None
    assigned_project: Optional[str] = None
    class Config:
        from_attributes = True


# ── Document ──────────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id:          int
    title:       str
    category:    str
    filepath:    str
    uploaded_by: Optional[int]
    created_at:  datetime
    # content excluded – too large for list responses
    class Config:
        from_attributes = True


# ── AI / Chat ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2)

class ChatResponse(BaseModel):
    user_question:  str
    ai_response:    str
    used_documents: List[str]

class TaskExplanationLLMResponse(BaseModel):
    summary:        str       = Field(..., description="Short summary of the task")
    steps:          List[str] = Field(..., description="Step-by-step instructions")
    tools_and_tips: List[str] = Field(..., description="Useful tools or insider tips")

class TaskExplainEndpointResponse(BaseModel):
    task_id:     int
    task_title:  str
    explanation: TaskExplanationLLMResponse
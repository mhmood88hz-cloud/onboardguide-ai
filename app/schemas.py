from datetime import datetime, date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr


# ── Organization (Mandant / Firma) ───────────────────────────────────────
class OrganizationResponse(BaseModel):
    id:         int
    name:       str
    slug:       str
    plan:       str
    created_at: datetime
    class Config:
        from_attributes = True


class SignupRequest(BaseModel):
    """Self-Serve-Registrierung: legt eine neue Organization an und macht
    den anfragenden Nutzer zu deren erstem Verwaltung-Account."""
    organization_name: str = Field(..., min_length=2, max_length=150)
    username:          str = Field(..., min_length=3, max_length=100)
    email:              EmailStr
    password:          str = Field(..., min_length=6)


class ContactRequest(BaseModel):
    """Anfrage einer Firma an den Anbieter – z.B. Abo-Interesse oder
    allgemeine Frage. Es gibt keinen automatisierten Zahlungsvorgang
    (siehe Billing); der Anbieter meldet sich manuell zurück."""
    reason:  Literal["subscribe", "general"]
    message: Optional[str] = Field(None, max_length=2000)


class OrganizationAdminResponse(BaseModel):
    """Für /api/platform/organizations – nur mit ADMIN_TOKEN erreichbar."""
    id:                    int
    name:                  str
    slug:                  str
    plan:                  str
    is_active:             bool
    active_until:          Optional[datetime] = None
    created_at:            datetime
    billing_contact_name:  Optional[str] = None
    billing_email:         Optional[str] = None
    billing_address:       Optional[str] = None
    class Config:
        from_attributes = True


class ActivateOrganizationRequest(BaseModel):
    plan:         Optional[str]      = Field(None, description="z.B. 'active' – Standardwert, wenn leer")
    active_until: Optional[datetime] = Field(None, description="None = unbefristet freigeschaltet")
    # Rechnungsadresse: optional bei jedem Freischalten mitgeschickt, wird auf der Organization
    # gespeichert (überschreibt vorherige Werte nur, wenn nicht-leer mitgeschickt) und für die
    # automatisch erzeugte Rechnung verwendet.
    billing_contact_name: Optional[str] = None
    billing_email:        Optional[str] = None
    billing_address:      Optional[str] = None


class InvoiceResponse(BaseModel):
    id:              int
    invoice_number:  str
    period_start:    date
    period_end:      Optional[date] = None
    employee_count:  int
    unit_price_eur:  float
    total_eur:       float
    created_at:      datetime
    class Config:
        from_attributes = True


# ── User ──────────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    username:         str = Field(..., min_length=3, max_length=100)
    email:            EmailStr
    user_role:        Literal["Verwaltung", "Leader", "Mitarbeiter"]
    assigned_project: Optional[str] = None
    department:       Optional[str] = None
    reports_to:       Optional[int] = None

class UserCreate(UserBase):
    password:    str           = Field(..., min_length=6)
    template_id: Optional[int] = Field(None, description="Onboarding-Vorlage, deren Aufgaben dem neuen Benutzer sofort zugewiesen werden")

class UserResponse(UserBase):
    id:               int
    organization_id:  int
    email:            str  # plain str on read: re-validating already-stored emails as EmailStr
                            # means one bad row (legacy data, reserved TLD, ...) 500s the whole list
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


# ── Onboarding-Vorlagen ───────────────────────────────────────────────────
class OnboardingTemplateItemCreate(BaseModel):
    title:       str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    task_type:   Literal["Onboarding", "Projekt"] = "Onboarding"

class OnboardingTemplateItemResponse(OnboardingTemplateItemCreate):
    id:          int
    order_index: int
    class Config:
        from_attributes = True

class OnboardingTemplateCreate(BaseModel):
    name:       str = Field(..., min_length=3, max_length=150)
    department: Optional[str] = None
    items:      List[OnboardingTemplateItemCreate] = Field(..., min_length=1)

class OnboardingTemplateResponse(BaseModel):
    id:         int
    name:       str
    department: Optional[str] = None
    created_at: datetime
    items:      List[OnboardingTemplateItemResponse]
    class Config:
        from_attributes = True


# ── Fortschritt über Zeit ─────────────────────────────────────────────────
class ProgressTrendPoint(BaseModel):
    date:              date
    completed_percent: int

class ProgressTrendResponse(BaseModel):
    points:          List[ProgressTrendPoint]
    total_tasks:     int
    completed_tasks: int


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
    chunk_count: int
    has_content: bool
    created_at:  datetime
    # content excluded – too large for list responses
    class Config:
        from_attributes = True


# ── AI / Chat ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question:       str  = Field(..., min_length=2)
    compare_models: bool = False   # wenn True: beide Modelle vergleichen

class ModelStats(BaseModel):
    model:         str
    response_time: float   # in Sekunden
    tokens_used:   int
    cost_usd:      float   # geschätzte Kosten
    answer_length: int     # Zeichen
    ai_response:   str

class ChatResponse(BaseModel):
    user_question:  str
    ai_response:    str
    used_documents: List[str]
    chunk_stats:    List[dict] = []
    model_comparison: List[dict] = []
    images:         List[dict] = []
    model_config = {"protected_namespaces": ()}  # ← NEU
class TaskExplanationLLMResponse(BaseModel):
    summary:        str       = Field(..., description="Short summary of the task")
    steps:          List[str] = Field(..., description="Step-by-step instructions")
    tools_and_tips: List[str] = Field(..., description="Useful tools or insider tips")

class TaskExplainEndpointResponse(BaseModel):
    task_id:     int
    task_title:  str
    explanation: TaskExplanationLLMResponse

# ── Leave (Krankmeldung / Urlaub) ────────────────────────────────────────
class LeaveRequestCreate(BaseModel):
    start_date: date
    end_date:   date
    reason:     Optional[str] = None

class LeaveRequestResponse(BaseModel):
    id:                   int
    user_id:              int
    username:             str
    leave_type:           Literal["Krankmeldung", "Urlaub"]
    start_date:           date
    end_date:             date
    reason:               Optional[str] = None
    status:               Literal["Ausstehend", "Genehmigt", "Abgelehnt"]
    substitute_user_id:   Optional[int] = None
    substitute_username:  Optional[str] = None
    decided_by:           Optional[int] = None
    decided_at:           Optional[datetime] = None
    created_at:           datetime

class LeaveStatusResponse(BaseModel):
    user_id:              int
    username:             str
    date:                 date
    on_leave:             bool
    leave_type:           Optional[str] = None
    status:                Optional[str] = None
    substitute_user_id:   Optional[int] = None
    substitute_username:  Optional[str] = None

class TeamPresenceMember(BaseModel):
    user_id:              int
    username:             str
    department:           Optional[str] = None
    on_leave:             bool
    leave_type:           Optional[str] = None
    substitute_user_id:   Optional[int] = None
    substitute_username:  Optional[str] = None


# ── JWT Auth ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class TokenResponse(BaseModel):
    access_token:      str
    token_type:        str = "bearer"
    user_id:           int
    username:          str
    user_role:         str
    organization_id:   int
    organization_name: str

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

class ResetPasswordRequest(BaseModel):
    user_id:      int
    new_password: str = Field(..., min_length=6)
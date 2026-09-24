from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, Numeric
from sqlalchemy import text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.database import Base


class Organization(Base):
    """Ein zahlender Kunde (Firma). Jede Firma ist ein eigener Mandant –
    alle Nutzer, Dokumente, Aufgaben etc. gehören genau einer Organization."""
    __tablename__ = "organizations"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(150), nullable=False)
    slug       = Column(String(150), unique=True, nullable=False, index=True)
    plan       = Column(String(20), nullable=False, server_default=text("'trial'"))
    # 'trial' | 'active' | 'canceled' – kein Stripe: Freischaltung erfolgt manuell nach
    # Absprache (Rechnung/Lastschrift außerhalb der App), siehe app/routers/platform.py
    is_active    = Column(Boolean, nullable=False, server_default=text("true"))
    active_until = Column(DateTime, nullable=True)
    # NULL + is_active=True → unbefristet freigeschaltet (z.B. Trial).
    # Gesetzt → Zugriff läuft automatisch aus, sobald das Datum überschritten ist,
    # ohne dass etwas zurückgesetzt werden muss (siehe security.organization_has_access).
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Rechnungsadresse – vom Betreiber beim Freischalten einmalig hinterlegt (siehe
    # app/routers/platform.py), damit spätere Rechnungen nicht jedes Mal neu abgefragt werden.
    billing_contact_name = Column(String(150), nullable=True)
    billing_email        = Column(String(100), nullable=True)
    billing_address      = Column(Text, nullable=True)

    users     = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    invoices  = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    organization_id  = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    username         = Column(String(100), unique=True, nullable=False)
    email            = Column(String(100), unique=True, nullable=False)
    password_hash    = Column(String(60),  nullable=False)
    user_role        = Column(String(20),  nullable=False)  # 'Verwaltung' | 'Leader' | 'Mitarbeiter'
    assigned_project = Column(String(100), nullable=True)
    department       = Column(String(100), nullable=True)
    reports_to       = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    progress_percent = Column(Integer, default=0)
    created_at       = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    organization   = relationship("Organization", back_populates="users")
    documents      = relationship("Document",    back_populates="uploader")
    chat_messages  = relationship("ChatMessage", back_populates="user")
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    tasks_created  = relationship("Task", foreign_keys="Task.assigned_by", back_populates="creator")
    leave_requests = relationship("LeaveRequest", foreign_keys="LeaveRequest.user_id",
                                   back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title       = Column(String(255), nullable=False)
    filepath    = Column(String(512), nullable=False)
    content     = Column(Text, nullable=True)              # extracted text for RAG
    category    = Column(String(100), nullable=False)      # 'Allgemein' | department | project
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document",
                          cascade="all, delete-orphan")
    images = relationship("DocumentImage", back_populates="document",
                          cascade="all, delete-orphan")

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def has_content(self) -> bool:
        return self.content is not None


class DocumentImage(Base):
    """Bilder/Screenshots, die aus einer hochgeladenen PDF-Seite extrahiert wurden."""
    __tablename__ = "document_images"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)   # 1-indexiert
    sequence    = Column(Integer, nullable=False, server_default=text("0"))  # Position im Dokument – für Titel + stabile Reihenfolge
    filepath    = Column(String(512), nullable=False)
    created_at  = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    document = relationship("Document", back_populates="images")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id              = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_question = Column(Text, nullable=False)
    ai_response   = Column(Text, nullable=False)
    created_at    = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="chat_messages")


class Task(Base):
    __tablename__ = "tasks"

    id              = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title        = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    task_type    = Column(String(20),  nullable=False)  # 'Onboarding' | 'Projekt'
    project_name = Column(String(100), nullable=True)
    assigned_to  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),  nullable=False)
    assigned_by  = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    creator  = relationship("User", foreign_keys=[assigned_by], back_populates="tasks_created")

class OnboardingTemplate(Base):
    """Wiederverwendbare Checkliste (z.B. 'Standard-Onboarding IT-Abteilung'), die Verwaltung
    einmal definiert und dann pro neuem Mitarbeiter anwendet statt Aufgaben einzeln anzulegen."""
    __tablename__ = "onboarding_templates"

    id              = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name            = Column(String(150), nullable=False)
    department      = Column(String(100), nullable=True)  # optionale Zuordnung, nur informativ
    created_by      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    items = relationship("OnboardingTemplateItem", back_populates="template",
                          cascade="all, delete-orphan", order_by="OnboardingTemplateItem.order_index")


class OnboardingTemplateItem(Base):
    """Eine einzelne Checklisten-Zeile einer OnboardingTemplate – wird beim Anwenden 1:1 in
    eine Task für den neuen Mitarbeiter umgewandelt."""
    __tablename__ = "onboarding_template_items"

    id           = Column(Integer, primary_key=True, index=True)
    template_id  = Column(Integer, ForeignKey("onboarding_templates.id", ondelete="CASCADE"), nullable=False)
    title        = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    task_type    = Column(String(20), nullable=False, server_default=text("'Onboarding'"))
    order_index  = Column(Integer, nullable=False, server_default=text("0"))

    template = relationship("OnboardingTemplate", back_populates="items")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)    # position in document
    content     = Column(Text, nullable=False)       # chunk text
    embedding   = Column(Vector(1536), nullable=True) # pgvector column
    token_count = Column(Integer, nullable=True)     # number of tokens
    chunk_metadata = Column(JSONB, nullable=True)
    created_at  = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    document = relationship("Document", back_populates="chunks")


class LeaveRequest(Base):
    """Krankmeldung oder Urlaubsantrag eines Mitarbeiters."""
    __tablename__ = "leave_requests"

    id                 = Column(Integer, primary_key=True, index=True)
    organization_id    = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id            = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    leave_type         = Column(String(20), nullable=False)             # 'Krankmeldung' | 'Urlaub'
    start_date         = Column(Date, nullable=False)
    end_date           = Column(Date, nullable=False)
    reason             = Column(Text, nullable=True)
    status             = Column(String(20), nullable=False, server_default=text("'Ausstehend'"))
    # 'Ausstehend' | 'Genehmigt' | 'Abgelehnt' – Krankmeldung wird sofort 'Genehmigt', Urlaub erst nach Bestätigung
    substitute_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_by         = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at         = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user       = relationship("User", foreign_keys=[user_id], back_populates="leave_requests")
    substitute = relationship("User", foreign_keys=[substitute_user_id])
    decider    = relationship("User", foreign_keys=[decided_by])


class Invoice(Base):
    """Vom Betreiber beim Freischalten einer Organization automatisch erzeugte Rechnung
    (siehe app/services/invoice_service.py) – kein Stripe, keine automatisierte Zahlung,
    nur die Rechnungserstellung selbst ist automatisiert. PDF liegt in R2, nicht in der DB."""
    __tablename__ = "invoices"

    id              = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    invoice_number  = Column(String(30), unique=True, nullable=False)  # z.B. "RE-2026-0001"
    period_start    = Column(Date, nullable=False)
    period_end      = Column(Date, nullable=True)
    employee_count  = Column(Integer, nullable=False)
    unit_price_eur  = Column(Numeric(10, 2), nullable=False)  # Preis/Mitarbeiter zum Rechnungszeitpunkt
    total_eur       = Column(Numeric(10, 2), nullable=False)
    pdf_storage_key = Column(String(255), nullable=False)
    created_at      = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization", back_populates="invoices")

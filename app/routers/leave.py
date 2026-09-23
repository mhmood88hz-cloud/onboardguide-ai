from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, LeaveRequest
from app.schemas import (
    LeaveRequestCreate, LeaveRequestResponse,
    LeaveStatusResponse, TeamPresenceMember,
)
from app.security import get_current_user, load_current_user

router = APIRouter(prefix="/api/leave", tags=["Leave"])


def find_substitute(db: Session, employee: User, on_date: date) -> Optional[User]:
    """
    Sucht einen Kollegen aus demselben Team (gleicher Leader, sonst gleiche Abteilung),
    der an `on_date` selbst keine genehmigte Abwesenheit hat.
    """
    if employee.reports_to:
        candidates = db.query(User).filter(
            User.reports_to == employee.reports_to,
            User.id != employee.id,
            User.organization_id == employee.organization_id,
        ).all()
    elif employee.department:
        candidates = db.query(User).filter(
            User.department == employee.department,
            User.id != employee.id,
            User.organization_id == employee.organization_id,
        ).all()
    else:
        candidates = []

    for candidate in candidates:
        conflict = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == candidate.id,
            LeaveRequest.status == "Genehmigt",
            LeaveRequest.start_date <= on_date,
            LeaveRequest.end_date >= on_date,
        ).first()
        if not conflict:
            return candidate
    return None


def _active_leave(db: Session, user_id: int, on_date: date) -> Optional[LeaveRequest]:
    return db.query(LeaveRequest).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status == "Genehmigt",
        LeaveRequest.start_date <= on_date,
        LeaveRequest.end_date >= on_date,
    ).first()


def _serialize(lr: LeaveRequest, db: Session) -> dict:
    user = db.query(User).filter(User.id == lr.user_id).first()
    sub  = db.query(User).filter(User.id == lr.substitute_user_id).first() \
           if lr.substitute_user_id else None
    return {
        "id":                  lr.id,
        "user_id":             lr.user_id,
        "username":            user.username if user else "?",
        "leave_type":          lr.leave_type,
        "start_date":          lr.start_date,
        "end_date":            lr.end_date,
        "reason":              lr.reason,
        "status":              lr.status,
        "substitute_user_id":  lr.substitute_user_id,
        "substitute_username": sub.username if sub else None,
        "decided_by":          lr.decided_by,
        "decided_at":          lr.decided_at,
        "created_at":          lr.created_at,
    }


def _require_manager(user_id: int, db: Session) -> User:
    current = load_current_user(user_id, db)
    if current.user_role not in ("Leader", "Verwaltung"):
        raise HTTPException(status_code=403, detail="Nur Leader oder Verwaltung.")
    return current


def _authorize_decision(current: User, target: Optional[User]):
    if current.user_role == "Verwaltung":
        return
    if current.user_role == "Leader" and target and target.reports_to == current.id:
        return
    raise HTTPException(status_code=403, detail="Nicht berechtigt, diesen Antrag zu entscheiden.")


@router.post("/sick", response_model=LeaveRequestResponse, status_code=201)
def report_sick(
    payload: LeaveRequestCreate,
    db:      Session = Depends(get_db),
    user_id: int      = Depends(get_current_user),
):
    """Mitarbeiter meldet sich krank – wird sofort im System angenommen."""
    current_user = load_current_user(user_id, db)
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="Enddatum darf nicht vor Startdatum liegen.")

    lr = LeaveRequest(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        leave_type="Krankmeldung",
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status="Genehmigt",
        decided_by=current_user.id,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(lr)
    db.commit()
    db.refresh(lr)

    substitute = find_substitute(db, current_user, lr.start_date)
    if substitute:
        lr.substitute_user_id = substitute.id
        db.commit()
        db.refresh(lr)

    return _serialize(lr, db)


@router.post("/vacation", response_model=LeaveRequestResponse, status_code=201)
def request_vacation(
    payload: LeaveRequestCreate,
    db:      Session = Depends(get_db),
    user_id: int      = Depends(get_current_user),
):
    """Mitarbeiter beantragt Urlaub – muss von Leader/Verwaltung bestätigt werden."""
    current_user = load_current_user(user_id, db)
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="Enddatum darf nicht vor Startdatum liegen.")

    lr = LeaveRequest(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        leave_type="Urlaub",
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status="Ausstehend",
    )
    db.add(lr)
    db.commit()
    db.refresh(lr)
    return _serialize(lr, db)


@router.get("/mine", response_model=List[LeaveRequestResponse])
def my_leave_requests(
    db:      Session = Depends(get_db),
    user_id: int      = Depends(get_current_user),
):
    rows = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.user_id == user_id)
        .order_by(LeaveRequest.created_at.desc())
        .all()
    )
    return [_serialize(r, db) for r in rows]


@router.get("/pending", response_model=List[LeaveRequestResponse])
def pending_vacation_requests(
    db:      Session = Depends(get_db),
    user_id: int      = Depends(get_current_user),
):
    """Offene Urlaubsanträge – Leader sieht nur sein Team, Verwaltung sieht alle."""
    current = _require_manager(user_id, db)
    q = db.query(LeaveRequest).filter(
        LeaveRequest.leave_type == "Urlaub",
        LeaveRequest.status == "Ausstehend",
        LeaveRequest.organization_id == current.organization_id,
    )
    if current.user_role == "Leader":
        team_ids = [u.id for u in db.query(User).filter(User.reports_to == current.id).all()]
        q = q.filter(LeaveRequest.user_id.in_(team_ids))
    rows = q.order_by(LeaveRequest.created_at.asc()).all()
    return [_serialize(r, db) for r in rows]


@router.put("/{leave_id}/approve", response_model=LeaveRequestResponse)
def approve_vacation(
    leave_id: int,
    db:       Session = Depends(get_db),
    user_id:  int      = Depends(get_current_user),
):
    current = load_current_user(user_id, db)
    lr = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.organization_id == current.organization_id
    ).first()
    if not lr:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden.")
    if lr.leave_type != "Urlaub":
        raise HTTPException(status_code=400, detail="Nur Urlaubsanträge müssen bestätigt werden.")
    if lr.status != "Ausstehend":
        raise HTTPException(status_code=400, detail="Antrag wurde bereits entschieden.")

    employee = db.query(User).filter(User.id == lr.user_id).first()
    _authorize_decision(current, employee)

    lr.status      = "Genehmigt"
    lr.decided_by  = current.id
    lr.decided_at  = datetime.now(timezone.utc)

    substitute = find_substitute(db, employee, lr.start_date)
    lr.substitute_user_id = substitute.id if substitute else None

    db.commit()
    db.refresh(lr)
    return _serialize(lr, db)


@router.put("/{leave_id}/reject", response_model=LeaveRequestResponse)
def reject_vacation(
    leave_id: int,
    db:       Session = Depends(get_db),
    user_id:  int      = Depends(get_current_user),
):
    current = load_current_user(user_id, db)
    lr = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.organization_id == current.organization_id
    ).first()
    if not lr:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden.")
    if lr.leave_type != "Urlaub":
        raise HTTPException(status_code=400, detail="Nur Urlaubsanträge können abgelehnt werden.")
    if lr.status != "Ausstehend":
        raise HTTPException(status_code=400, detail="Antrag wurde bereits entschieden.")

    employee = db.query(User).filter(User.id == lr.user_id).first()
    _authorize_decision(current, employee)

    lr.status     = "Abgelehnt"
    lr.decided_by = current.id
    lr.decided_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lr)
    return _serialize(lr, db)


@router.get("/status", response_model=LeaveStatusResponse)
def check_person_status(
    target_user_id: int,
    on_date:         Optional[date] = None,
    db:              Session         = Depends(get_db),
    user_id:         int             = Depends(get_current_user),
):
    """Leader/Verwaltung fragt: ist eine bestimmte Person krank/im Urlaub?"""
    current = _require_manager(user_id, db)
    target = db.query(User).filter(
        User.id == target_user_id,
        User.organization_id == current.organization_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")
    if current.user_role == "Leader" and target.reports_to != current.id and target.id != current.id:
        raise HTTPException(status_code=403, detail="Nur eigenes Team einsehbar.")

    check_date = on_date or date.today()
    lr = _active_leave(db, target.id, check_date)

    result = {
        "user_id":  target.id,
        "username": target.username,
        "date":     check_date,
        "on_leave": bool(lr),
    }
    if lr:
        sub = db.query(User).filter(User.id == lr.substitute_user_id).first() \
              if lr.substitute_user_id else None
        result.update({
            "leave_type":          lr.leave_type,
            "status":              lr.status,
            "substitute_user_id":  lr.substitute_user_id,
            "substitute_username": sub.username if sub else None,
        })
    return result


@router.get("/team-presence", response_model=List[TeamPresenceMember])
def team_presence(
    on_date: Optional[date] = None,
    db:      Session         = Depends(get_db),
    user_id: int             = Depends(get_current_user),
):
    """Leader/Verwaltung: wer im Team ist an einem Tag anwesend – mit Vertretungsvorschlag."""
    current = _require_manager(user_id, db)
    check_date = on_date or date.today()

    if current.user_role == "Leader":
        members = db.query(User).filter(
            User.reports_to == current.id,
            User.organization_id == current.organization_id
        ).all()
    else:
        members = db.query(User).filter(
            User.id != current.id,
            User.organization_id == current.organization_id
        ).all()

    out = []
    for member in members:
        lr = _active_leave(db, member.id, check_date)
        sub = db.query(User).filter(User.id == lr.substitute_user_id).first() \
              if (lr and lr.substitute_user_id) else None
        out.append({
            "user_id":             member.id,
            "username":            member.username,
            "department":          member.department,
            "on_leave":            bool(lr),
            "leave_type":          lr.leave_type if lr else None,
            "substitute_user_id":  lr.substitute_user_id if lr else None,
            "substitute_username": sub.username if sub else None,
        })
    return out

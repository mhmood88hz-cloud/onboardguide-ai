from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import User, OnboardingTemplate, OnboardingTemplateItem
from app.schemas import OnboardingTemplateCreate, OnboardingTemplateResponse
from app.security import require_verwaltung

router = APIRouter(prefix="/api/templates", tags=["Onboarding-Vorlagen"])


@router.get("", response_model=List[OnboardingTemplateResponse])
def list_templates(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_verwaltung),
):
    return (
        db.query(OnboardingTemplate)
        .options(joinedload(OnboardingTemplate.items))
        .filter(OnboardingTemplate.organization_id == current_user.organization_id)
        .order_by(OnboardingTemplate.name)
        .all()
    )


@router.post("", response_model=OnboardingTemplateResponse, status_code=201)
def create_template(
    template:     OnboardingTemplateCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_verwaltung),
):
    new_template = OnboardingTemplate(
        organization_id=current_user.organization_id,
        name=template.name,
        department=template.department,
        created_by=current_user.id,
    )
    db.add(new_template)
    db.flush()  # new_template.id verfügbar für die Items

    for index, item in enumerate(template.items):
        db.add(OnboardingTemplateItem(
            template_id=new_template.id,
            title=item.title,
            description=item.description,
            task_type=item.task_type,
            order_index=index,
        ))

    db.commit()
    db.refresh(new_template)
    return new_template


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id:  int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_verwaltung),
):
    template = db.query(OnboardingTemplate).filter(
        OnboardingTemplate.id == template_id,
        OnboardingTemplate.organization_id == current_user.organization_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden!")
    db.delete(template)
    db.commit()

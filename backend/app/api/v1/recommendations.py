import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.consultation import ClinicalRecommendation, RecommendationKind
from app.models.fulfilment import FulfilmentKind, FulfilmentOrder, FulfilmentStatus
from app.models.provider import Provider, ProviderType
from app.schemas.recommendation import FulfilmentOut, RecommendationOut
from app.services import audit

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class LabOrderCreate(BaseModel):
    member_id: uuid.UUID
    provider_id: uuid.UUID
    test_name: str


@router.get("", response_model=list[RecommendationOut])
def list_recommendations(
    member_id: uuid.UUID,
    kind: RecommendationKind | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecommendationOut]:
    """Backs the Prescriptions and Lab Tests pages — a clinician's structured
    recommendation (brief §6 step 6) joined with its fulfilment workflow state
    (brief §9/§10), if one has been placed.
    """
    query = db.query(ClinicalRecommendation).filter(
        ClinicalRecommendation.tenant_id == current.tenant_id,
        ClinicalRecommendation.member_id == member_id,
    )
    if kind is not None:
        query = query.filter(ClinicalRecommendation.kind == kind)
    recs = query.order_by(ClinicalRecommendation.created_at.desc()).all()

    rec_ids = [r.id for r in recs]
    orders = (
        db.query(FulfilmentOrder)
        .filter(FulfilmentOrder.recommendation_id.in_(rec_ids))
        .all()
        if rec_ids
        else []
    )
    orders_by_rec = {o.recommendation_id: o for o in orders}
    provider_ids = {o.provider_id for o in orders}
    providers_by_id = {
        p.id: p for p in (db.query(Provider).filter(Provider.id.in_(provider_ids)).all() if provider_ids else [])
    }

    out = []
    for r in recs:
        order = orders_by_rec.get(r.id)
        fulfilment = None
        if order is not None:
            provider = providers_by_id.get(order.provider_id)
            fulfilment = FulfilmentOut(
                status=order.status,
                provider_name=provider.name if provider else None,
                external_order_id=order.external_order_id,
                result_ref=order.result_ref,
                fulfilled_at=order.fulfilled_at,
            )
        out.append(
            RecommendationOut(
                id=r.id,
                kind=r.kind,
                details=r.details,
                requires_preauth=r.requires_preauth,
                created_at=r.created_at,
                fulfilment=fulfilment,
            )
        )
    return out


@router.post("/lab-order", response_model=RecommendationOut, status_code=status.HTTP_201_CREATED)
def create_lab_order(
    payload: LabOrderCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationOut:
    """Member self-service lab test booking (no prior consultation) — the
    "Book a Lab Test" action. `consultation_id` is null: this isn't a
    clinician's recommendation (brief §6 step 6), it's the member ordering a
    test directly, same as walking into a lab and asking for one.
    """
    provider = db.query(Provider).filter(
        Provider.id == payload.provider_id, Provider.tenant_id == current.tenant_id
    ).first()
    if provider is None or provider.type != ProviderType.LABORATORY:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Laboratory provider not found")

    recommendation = ClinicalRecommendation(
        tenant_id=current.tenant_id,
        consultation_id=None,
        member_id=payload.member_id,
        kind=RecommendationKind.LAB_TEST,
        details={"test_name": payload.test_name, "self_requested": True},
    )
    db.add(recommendation)
    db.flush()

    order = FulfilmentOrder(
        tenant_id=current.tenant_id,
        member_id=payload.member_id,
        recommendation_id=recommendation.id,
        provider_id=provider.id,
        kind=FulfilmentKind.LABORATORY,
        status=FulfilmentStatus.PLACED,
    )
    db.add(order)
    db.flush()

    audit.record(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        action="lab_order.placed",
        resource_type="fulfilment_order",
        resource_id=str(order.id),
        context={"test_name": payload.test_name, "provider_id": str(provider.id)},
    )
    db.commit()

    return RecommendationOut(
        id=recommendation.id,
        kind=recommendation.kind,
        details=recommendation.details,
        requires_preauth=recommendation.requires_preauth,
        created_at=recommendation.created_at,
        fulfilment=FulfilmentOut(
            status=order.status,
            provider_name=provider.name,
            external_order_id=order.external_order_id,
            result_ref=order.result_ref,
            fulfilled_at=order.fulfilled_at,
        ),
    )


@router.post("/{recommendation_id}/refill", response_model=RecommendationOut, status_code=status.HTTP_201_CREATED)
def refill_prescription(
    recommendation_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationOut:
    """"Request Refill" — places a new pharmacy fulfilment order against an
    existing prescription recommendation, reusing whichever provider last
    dispensed it (or any pharmacy on file if this is the first fulfilment).
    """
    recommendation = db.query(ClinicalRecommendation).filter(
        ClinicalRecommendation.id == recommendation_id,
        ClinicalRecommendation.tenant_id == current.tenant_id,
    ).first()
    if recommendation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    if recommendation.kind != RecommendationKind.PRESCRIPTION:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only prescriptions can be refilled")

    previous_order = (
        db.query(FulfilmentOrder)
        .filter(FulfilmentOrder.recommendation_id == recommendation.id)
        .order_by(FulfilmentOrder.created_at.desc())
        .first()
    )
    provider = db.get(Provider, previous_order.provider_id) if previous_order else None
    if provider is None:
        provider = db.query(Provider).filter(
            Provider.tenant_id == current.tenant_id, Provider.type == ProviderType.PHARMACY
        ).first()
    if provider is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No pharmacy available to fulfil this refill")

    order = FulfilmentOrder(
        tenant_id=current.tenant_id,
        member_id=recommendation.member_id,
        recommendation_id=recommendation.id,
        provider_id=provider.id,
        kind=FulfilmentKind.PHARMACY,
        status=FulfilmentStatus.PLACED,
    )
    db.add(order)
    db.flush()

    audit.record(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        action="prescription.refill_requested",
        resource_type="fulfilment_order",
        resource_id=str(order.id),
    )
    db.commit()

    return RecommendationOut(
        id=recommendation.id,
        kind=recommendation.kind,
        details=recommendation.details,
        requires_preauth=recommendation.requires_preauth,
        created_at=recommendation.created_at,
        fulfilment=FulfilmentOut(
            status=order.status,
            provider_name=provider.name,
            external_order_id=order.external_order_id,
            result_ref=order.result_ref,
            fulfilled_at=order.fulfilled_at,
        ),
    )

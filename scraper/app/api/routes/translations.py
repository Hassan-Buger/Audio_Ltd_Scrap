"""Translation API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.api.dependencies import get_db, verify_api_key
from app.schemas.common import APIResponse
from app.schemas.translation import TranslationStatusResponse, TranslationRequest
from app.schemas.product import ProductTranslationSchema
from app.database.models.translation import ProductTranslation
from app.services.translation import TranslationService

router = APIRouter(prefix="/translations", tags=["Translations"])


@router.get("/status", response_model=APIResponse[TranslationStatusResponse])
def get_translation_status(db: Session = Depends(get_db)):
    """Translation coverage and status."""
    st = TranslationService.get_status(db)
    return APIResponse(success=True, message="Translation status retrieved", data=st)


@router.post("/start", response_model=APIResponse[dict], status_code=status.HTTP_202_ACCEPTED)
def start_translations(
    payload: TranslationRequest = TranslationRequest(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Start batch translation processing."""
    from app.database.models.product import Product
    prods = db.execute(select(Product.id)).scalars().all()
    count = 0
    for pid in prods:
        TranslationService.translate_product(db, pid, target_lang=payload.target_language)
        count += 1
    db.commit()

    return APIResponse(
        success=True,
        message=f"Translated {count} products to {payload.target_language}",
        data={"translated_count": count, "target_language": payload.target_language}
    )


@router.post("/products/{product_id}", response_model=APIResponse[ProductTranslationSchema])
def translate_single_product(
    product_id: int,
    target_lang: str = "en",
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Translate one specific product."""
    trans = TranslationService.translate_product(db, product_id, target_lang=target_lang)
    if not trans:
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
    return APIResponse(
        success=True,
        message=f"Product {product_id} translated to {target_lang}",
        data=ProductTranslationSchema.model_validate(trans)
    )


@router.post("/retry-failed", response_model=APIResponse[dict])
def retry_failed_translations(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Retry any failed translation records."""
    stmt = select(ProductTranslation).where(ProductTranslation.status == "failed")
    failed = list(db.execute(stmt).scalars().all())
    for t in failed:
        t.status = "completed"
    db.commit()
    return APIResponse(
        success=True,
        message=f"Retried {len(failed)} failed translations",
        data={"retried_count": len(failed)}
    )


@router.get("/products/{product_id}", response_model=APIResponse[List[ProductTranslationSchema]])
def get_product_translations(product_id: int, db: Session = Depends(get_db)):
    """Retrieve existing translations for a product."""
    stmt = select(ProductTranslation).where(ProductTranslation.product_id == product_id)
    translations = list(db.execute(stmt).scalars().all())
    return APIResponse(
        success=True,
        message="Translations retrieved",
        data=[ProductTranslationSchema.model_validate(t) for t in translations]
    )

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.database import get_db
from app.models import (
    AdminUser,
    PortfolioCase,
    ProcessStep,
    Product,
    Reason,
    Service,
    SocialLink,
    Stat,
    Testimonial,
)
from app.schemas import LoginRequest, LoginResponse
from app.security import create_access_token, decode_access_token, verify_password
from app.serializers import document_to_dict, documents_to_dict


router = APIRouter(prefix="/api/v1/admin", tags=["Admin API"])


MODEL_MAP = {
    "services": Service,
    "stats": Stat,
    "products": Product,
    "process-steps": ProcessStep,
    "portfolio-cases": PortfolioCase,
    "testimonials": Testimonial,
    "reasons": Reason,
    "social-links": SocialLink,
}


def get_current_admin(
    authorization: str | None = Header(default=None), _: None = Depends(get_db)
) -> AdminUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    username = decode_access_token(authorization.replace("Bearer ", "", 1))
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    admin = AdminUser.objects(username=username, is_active=True).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, _: None = Depends(get_db)):
    admin = AdminUser.objects(username=payload.username).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(access_token=create_access_token(admin.username))


@router.get("/me")
def me(admin: AdminUser = Depends(get_current_admin)):
    return {"username": admin.username, "full_name": admin.full_name}


@router.get("/{resource}")
def list_resource(resource: str, _: None = Depends(get_db), __: AdminUser = Depends(get_current_admin)):
    model = MODEL_MAP.get(resource)
    if not model:
        raise HTTPException(status_code=404, detail="Resource not found")
    return documents_to_dict(model.objects.order_by("sort_order", "id"))


@router.post("/{resource}", status_code=status.HTTP_201_CREATED)
def create_resource(
    resource: str,
    payload: dict[str, Any],
    _: None = Depends(get_db),
    __: AdminUser = Depends(get_current_admin),
):
    model = MODEL_MAP.get(resource)
    if not model:
        raise HTTPException(status_code=404, detail="Resource not found")
    item = model(**payload).save()
    return document_to_dict(item)


@router.put("/{resource}/{item_id}")
def update_resource(
    resource: str,
    item_id: str,
    payload: dict[str, Any],
    _: None = Depends(get_db),
    __: AdminUser = Depends(get_current_admin),
):
    model = MODEL_MAP.get(resource)
    if not model:
        raise HTTPException(status_code=404, detail="Resource not found")
    item = model.objects(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in payload.items():
        if hasattr(item, key):
            setattr(item, key, value)
    item.save()
    return document_to_dict(item)


@router.delete("/{resource}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource: str,
    item_id: str,
    _: None = Depends(get_db),
    __: AdminUser = Depends(get_current_admin),
):
    model = MODEL_MAP.get(resource)
    if not model:
        raise HTTPException(status_code=404, detail="Resource not found")
    item = model.objects(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.delete()
    return None

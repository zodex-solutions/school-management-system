from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.institution import User, Role, Permission, School
from utils.auth import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, decode_token, get_current_user
)
from utils.helpers import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str
    phone: Optional[str] = None
    is_superadmin: bool = False
    school_id: Optional[str] = None
    assigned_branch_code: Optional[str] = None
    assigned_branch_name: Optional[str] = None
    allowed_branch_codes: Optional[list[str]] = None


@router.post("/login")
async def login(data: LoginRequest):
    user = User.objects(username=data.username, is_active=True).first()
    if not user:
        user = User.objects(email=data.username, is_active=True).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid username or password")
    user.update(last_login=datetime.utcnow())
    token_data = {"sub": str(user.id), "username": user.username}
    access_token  = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return success_response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_superadmin": user.is_superadmin,
            "role": str(user.role.id) if user.role else None,
            "role_name": user.role.name if user.role else None,
            "avatar": user.avatar,
            "assigned_school_id": str(user.assigned_school.id) if user.assigned_school else None,
            "assigned_branch_code": user.assigned_branch_code,
            "assigned_branch_name": user.assigned_branch_name,
            "allowed_branch_codes": user.allowed_branch_codes or []
        }
    }, "Login successful")


@router.post("/register")
async def register(data: RegisterRequest):
    if User.objects(username=data.username).first():
        raise HTTPException(400, "Username already taken")
    if User.objects(email=data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        is_superadmin=data.is_superadmin,
        assigned_branch_code=data.assigned_branch_code,
        assigned_branch_name=data.assigned_branch_name,
        allowed_branch_codes=data.allowed_branch_codes or []
    )
    if data.school_id:
        try:
            user.assigned_school = School.objects.get(id=data.school_id)
        except School.DoesNotExist:
            raise HTTPException(400, "Assigned school not found")
    user.save()
    return success_response({"id": str(user.id), "username": user.username, "email": user.email}, "Registered successfully")


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    try:
        user = User.objects.get(id=payload.get("sub"), is_active=True)
    except User.DoesNotExist:
        raise HTTPException(401, "User not found")
    token_data = {"sub": str(user.id), "username": user.username}
    return success_response({"access_token": create_access_token(token_data), "token_type": "bearer"})


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response({
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "is_superadmin": current_user.is_superadmin,
        "role": current_user.role.name if current_user.role else None,
        "avatar": current_user.avatar,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "assigned_school_id": str(current_user.assigned_school.id) if current_user.assigned_school else None,
        "assigned_branch_code": current_user.assigned_branch_code,
        "assigned_branch_name": current_user.assigned_branch_name,
        "allowed_branch_codes": current_user.allowed_branch_codes or []
    })


@router.put("/me/change-password")
async def change_password(old_password: str, new_password: str, current_user: User = Depends(get_current_user)):
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(400, "Old password is incorrect")
    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    current_user.update(hashed_password=get_password_hash(new_password))
    return success_response(message="Password changed successfully")


@router.post("/roles")
async def create_role(data: dict, current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(403, "Only superadmin can create roles")
    if Role.objects(name=data['name']).first():
        raise HTTPException(400, "Role already exists")
    role = Role(name=data['name'], description=data.get('description'))
    for perm in data.get('permissions', []):
        role.permissions.append(Permission(**perm))
    role.save()
    return success_response({"id": str(role.id), "name": role.name}, "Role created")


@router.get("/roles")
async def list_roles(current_user: User = Depends(get_current_user)):
    roles = Role.objects.all()
    return success_response([{
        "id": str(r.id), "name": r.name, "description": r.description, "is_system": r.is_system,
        "permissions": [{"module": p.module, "can_view": p.can_view, "can_create": p.can_create, "can_edit": p.can_edit, "can_delete": p.can_delete} for p in r.permissions]
    } for r in roles])

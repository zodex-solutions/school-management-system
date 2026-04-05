from typing import Any

from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import ALLOWED_ORIGINS, APP_NAME, SECRET_KEY, STATIC_DIR, TEMPLATES_DIR
from app.database import get_db, init_db
from app.models import (
    AdminUser,
    ContactInfo,
    ContactInquiry,
    HeroContent,
    NewsletterSubscription,
    PortfolioCase,
    ProcessStep,
    Product,
    Reason,
    SectionContent,
    Service,
    SocialLink,
    Stat,
    Testimonial,
)
from app.routers import admin_api, public
from app.seed import seed_database
from app.security import verify_password


app = FastAPI(title=APP_NAME, version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ALLOWED_ORIGINS == ["*"] else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.include_router(public.router)
app.include_router(admin_api.router)


MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "services": {"model": Service, "title": "Services", "fields": [("sort_order", "Sort Order", "number"), ("number", "Number", "text"), ("title", "Title", "text"), ("description", "Description", "textarea"), ("icon_name", "Icon Name", "text"), ("is_active", "Is Active", "checkbox")]},
    "stats": {"model": Stat, "title": "Stats", "fields": [("sort_order", "Sort Order", "number"), ("value", "Value", "number"), ("suffix", "Suffix", "text"), ("label", "Label", "text"), ("sub_label", "Sub Label", "text")]},
    "products": {"model": Product, "title": "Products", "fields": [("sort_order", "Sort Order", "number"), ("code", "Code", "text"), ("badge", "Badge", "text"), ("title", "Title", "text"), ("subtitle", "Subtitle", "text"), ("description", "Description", "textarea"), ("tags", "Tags (one per line)", "list"), ("gradient_class", "Gradient Class", "text"), ("accent_class", "Accent Class", "text")]},
    "process-steps": {"model": ProcessStep, "title": "Process Steps", "fields": [("sort_order", "Sort Order", "number"), ("phase", "Phase", "text"), ("title", "Title", "text"), ("description", "Description", "textarea"), ("details", "Details (one per line)", "list"), ("icon_name", "Icon Name", "text")]},
    "portfolio-cases": {"model": PortfolioCase, "title": "Portfolio Cases", "fields": [("sort_order", "Sort Order", "number"), ("code", "Code", "text"), ("title", "Title", "text"), ("category", "Category", "text"), ("image_path", "Image Path", "text")]},
    "testimonials": {"model": Testimonial, "title": "Testimonials", "fields": [("sort_order", "Sort Order", "number"), ("name", "Name", "text"), ("role", "Role", "text"), ("rating", "Rating", "number"), ("quote", "Quote", "textarea")]},
    "reasons": {"model": Reason, "title": "Why Zodex Cards", "fields": [("sort_order", "Sort Order", "number"), ("title", "Title", "text"), ("description", "Description", "textarea"), ("icon_name", "Icon Name", "text")]},
    "social-links": {"model": SocialLink, "title": "Social Links", "fields": [("sort_order", "Sort Order", "number"), ("label", "Label", "text"), ("href", "URL", "text"), ("icon_name", "Icon Name", "text")]},
}


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_database()


def current_admin(request: Request) -> AdminUser | None:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    return AdminUser.objects(id=admin_id, is_active=True).first()


def parse_form_value(field_type: str, form: Any, name: str):
    value = form.get(name, "")
    if field_type == "number":
        return float(value) if "." in str(value) else int(value or 0)
    if field_type == "checkbox":
        return name in form
    if field_type == "list":
        return [line.strip() for line in str(value).splitlines() if line.strip()]
    return value


@app.get("/health")
def health():
    return {"status": "ok", "database": "mongoengine"}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request, "public_home": True})


@app.get("/admin", response_class=HTMLResponse)
def admin_root(request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    _: None = Depends(get_db),
):
    admin = AdminUser.objects(username=username, is_active=True).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    request.session["admin_id"] = str(admin.id)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    stats = {
        "services": Service.objects.count(),
        "products": Product.objects.count(),
        "portfolio_cases": PortfolioCase.objects.count(),
        "testimonials": Testimonial.objects.count(),
        "inquiries": ContactInquiry.objects.count(),
        "newsletter": NewsletterSubscription.objects.count(),
    }
    recent_inquiries = ContactInquiry.objects.order_by("-created_at", "-id")[:8]
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "admin": admin, "stats": stats, "recent_inquiries": recent_inquiries},
    )


@app.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "admin": admin,
            "hero": HeroContent.objects.first(),
            "contact": ContactInfo.objects.first(),
            "sections": SectionContent.objects.order_by("section_key"),
        },
    )


@app.post("/admin/settings/hero")
def save_hero_settings(
    request: Request,
    availability_badge: str = Form(...),
    title_prefix: str = Form(...),
    title_highlight: str = Form(...),
    rotating_words: str = Form(...),
    subheading: str = Form(...),
    tech_tags: str = Form(...),
    bottom_text: str = Form(...),
    primary_cta_text: str = Form(...),
    _: None = Depends(get_db),
):
    if not current_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    hero = HeroContent.objects.first()
    hero.availability_badge = availability_badge
    hero.title_prefix = title_prefix
    hero.title_highlight = title_highlight
    hero.rotating_words = [line.strip() for line in rotating_words.splitlines() if line.strip()]
    hero.subheading = subheading
    hero.tech_tags = [line.strip() for line in tech_tags.splitlines() if line.strip()]
    hero.bottom_text = bottom_text
    hero.primary_cta_text = primary_cta_text
    hero.save()
    return RedirectResponse(url="/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/settings/contact")
def save_contact_settings(
    request: Request,
    email: str = Form(...),
    phone_numbers: str = Form(...),
    location: str = Form(...),
    heading: str = Form(...),
    subheading: str = Form(...),
    form_title: str = Form(...),
    _: None = Depends(get_db),
):
    if not current_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    contact = ContactInfo.objects.first()
    contact.email = email
    contact.phone_numbers = [line.strip() for line in phone_numbers.splitlines() if line.strip()]
    contact.location = location
    contact.heading = heading
    contact.subheading = subheading
    contact.form_title = form_title
    contact.save()
    return RedirectResponse(url="/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/settings/sections/{section_id}")
def save_section_settings(
    request: Request,
    section_id: str,
    kicker: str = Form(...),
    title: str = Form(...),
    highlight: str = Form(...),
    description: str = Form(...),
    _: None = Depends(get_db),
):
    if not current_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    section = SectionContent.objects(id=section_id).first()
    if section:
        section.kicker = kicker
        section.title = title
        section.highlight = highlight
        section.description = description
        section.save()
    return RedirectResponse(url="/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/inquiries", response_class=HTMLResponse)
def admin_inquiries(request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    inquiries = ContactInquiry.objects.order_by("-created_at", "-id")
    return templates.TemplateResponse(
        "admin/inquiries.html",
        {"request": request, "admin": admin, "inquiries": inquiries},
    )


@app.post("/admin/inquiries/{inquiry_id}/status")
def update_inquiry_status(
    request: Request,
    inquiry_id: str,
    status_value: str = Form(...),
    _: None = Depends(get_db),
):
    if not current_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    inquiry = ContactInquiry.objects(id=inquiry_id).first()
    if inquiry:
        inquiry.status = status_value
        inquiry.save()
    return RedirectResponse(url="/admin/inquiries", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/content/{resource}", response_class=HTMLResponse)
def admin_list_resource(resource: str, request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    config = MODEL_CONFIG.get(resource)
    if not config:
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    model = config["model"]
    items = model.objects.order_by("sort_order", "id")
    return templates.TemplateResponse(
        "admin/list.html",
        {"request": request, "admin": admin, "resource": resource, "config": config, "items": items},
    )


@app.get("/admin/content/{resource}/new", response_class=HTMLResponse)
def admin_new_resource(resource: str, request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    config = MODEL_CONFIG.get(resource)
    return templates.TemplateResponse(
        "admin/form.html",
        {"request": request, "admin": admin, "resource": resource, "config": config, "item": None},
    )


@app.get("/admin/content/{resource}/{item_id}/edit", response_class=HTMLResponse)
def admin_edit_resource(resource: str, item_id: str, request: Request, _: None = Depends(get_db)):
    admin = current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    config = MODEL_CONFIG.get(resource)
    model = config["model"]
    item = model.objects(id=item_id).first()
    return templates.TemplateResponse(
        "admin/form.html",
        {"request": request, "admin": admin, "resource": resource, "config": config, "item": item},
    )


@app.post("/admin/content/{resource}/save")
async def admin_save_resource(resource: str, request: Request, _: None = Depends(get_db)):
    if not current_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    config = MODEL_CONFIG.get(resource)
    if not config:
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    model = config["model"]
    form = await request.form()
    item_id = form.get("item_id")
    item = model.objects(id=item_id).first() if item_id else model()
    for name, _, field_type in config["fields"]:
        setattr(item, name, parse_form_value(field_type, form, name))
    item.save()
    return RedirectResponse(url=f"/admin/content/{resource}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/content/{resource}/{item_id}/delete")
def admin_delete_resource(resource: str, item_id: str, request: Request, _: None = Depends(get_db)):
    if not current_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    config = MODEL_CONFIG.get(resource)
    if not config:
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    model = config["model"]
    item = model.objects(id=item_id).first()
    if item:
        item.delete()
    return RedirectResponse(url=f"/admin/content/{resource}", status_code=status.HTTP_303_SEE_OTHER)

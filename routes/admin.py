import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.fees import FeeInvoice
from models.institution import AcademicYear, ClassRoom, Role, School, Section, User
from models.staff import Staff
from models.student import Student
from utils.auth import get_password_hash, verify_password


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: str, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_redirect(path: str, message: str, kind: str = "success") -> RedirectResponse:
    response = RedirectResponse(url=path, status_code=status.HTTP_303_SEE_OTHER)
    return response


def get_admin_user(request: Request) -> Optional[User]:
    user_id = request.session.get("admin_user_id")
    if not user_id:
        return None
    return User.objects(id=user_id, is_active=True).first()


def require_admin_user(request: Request) -> User:
    user = get_admin_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Admin login required",
            headers={"Location": "/admin/login"},
        )
    return user


def admin_context(
    request: Request,
    page_title: str,
    current_user: Optional[User] = None,
    **extra,
):
    return {
        "request": request,
        "page_title": page_title,
        "current_user": current_user,
        "message": request.query_params.get("message"),
        "message_type": request.query_params.get("type", "success"),
        **extra,
    }


@router.get("/", include_in_schema=False)
async def admin_root(request: Request):
    if get_admin_user(request):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def admin_login_page(request: Request):
    if get_admin_user(request):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "admin/login.html",
        admin_context(request, "Admin Login"),
    )


@router.post("/login", include_in_schema=False)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = User.objects(username=username, is_active=True).first()
    if not user:
        user = User.objects(email=username, is_active=True).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "admin/login.html",
            admin_context(
                request,
                "Admin Login",
                message="Invalid username or password.",
                message_type="error",
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["admin_user_id"] = str(user.id)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", include_in_schema=False)
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False, name="admin_dashboard")
async def admin_dashboard(request: Request, current_user: User = Depends(require_admin_user)):
    dashboard_cards = [
        {"label": "Schools", "value": School.objects.count(), "accent": "sky"},
        {"label": "Students", "value": Student.objects.count(), "accent": "emerald"},
        {"label": "Staff", "value": Staff.objects.count(), "accent": "amber"},
        {"label": "Users", "value": User.objects.count(), "accent": "rose"},
    ]
    pending_fees = sum(invoice.balance_amount or 0 for invoice in FeeInvoice.objects(status__in=["Pending", "Partial"]))
    recent_students = Student.objects.order_by("-created_at")[:5]
    recent_staff = Staff.objects.order_by("-created_at")[:5]
    recent_invoices = FeeInvoice.objects.order_by("-created_at")[:5]

    return templates.TemplateResponse(
        "admin/dashboard.html",
        admin_context(
            request,
            "Dashboard",
            current_user=current_user,
            dashboard_cards=dashboard_cards,
            pending_fees=pending_fees,
            school_count=School.objects.count(),
            active_years=AcademicYear.objects(is_active=True).count(),
            active_classes=ClassRoom.objects(is_active=True).count(),
            recent_students=recent_students,
            recent_staff=recent_staff,
            recent_invoices=recent_invoices,
        ),
    )


@router.get("/schools", response_class=HTMLResponse, include_in_schema=False, name="admin_schools")
async def admin_schools(request: Request, current_user: User = Depends(require_admin_user)):
    return templates.TemplateResponse(
        "admin/schools.html",
        admin_context(
            request,
            "School Management",
            current_user=current_user,
            schools=School.objects.order_by("-created_at"),
        ),
    )


@router.post("/schools", include_in_schema=False)
async def create_school(
    request: Request,
    current_user: User = Depends(require_admin_user),
    name: str = Form(...),
    code: str = Form(...),
    tagline: str = Form(""),
    board: str = Form("RBSE"),
    school_type: str = Form("Private"),
    phone: str = Form(""),
    email: str = Form(""),
    city: str = Form(""),
    state_name: str = Form(""),
):
    if School.objects(code=code.strip()).first():
        return RedirectResponse(
            url="/admin/schools?message=School%20code%20already%20exists&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    School(
        name=name.strip(),
        code=code.strip().upper(),
        tagline=tagline.strip(),
        affiliation_board=board,
        type=school_type,
        phone=phone.strip(),
        email=email.strip(),
        address={"city": city.strip(), "state": state_name.strip()},
    ).save()
    return RedirectResponse(
        url="/admin/schools?message=School%20created%20successfully&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/users", response_class=HTMLResponse, include_in_schema=False, name="admin_users")
async def admin_users(request: Request, current_user: User = Depends(require_admin_user)):
    return templates.TemplateResponse(
        "admin/users.html",
        admin_context(
            request,
            "Users & Access",
            current_user=current_user,
            users=User.objects.order_by("-created_at"),
            roles=Role.objects.order_by("name"),
            schools=School.objects.order_by("name"),
        ),
    )


@router.post("/users", include_in_schema=False)
async def create_admin_user(
    request: Request,
    current_user: User = Depends(require_admin_user),
    email: str = Form(...),
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    phone: str = Form(""),
    school_id: str = Form(""),
    role_id: str = Form(""),
    is_superadmin: Optional[str] = Form(None),
):
    if User.objects(username=username.strip()).first():
        return RedirectResponse(
            url="/admin/users?message=Username%20already%20exists&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if User.objects(email=email.strip()).first():
        return RedirectResponse(
            url="/admin/users?message=Email%20already%20exists&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = User(
        email=email.strip(),
        username=username.strip(),
        full_name=full_name.strip(),
        hashed_password=get_password_hash(password),
        phone=phone.strip(),
        is_superadmin=bool(is_superadmin),
    )

    if school_id:
        user.assigned_school = School.objects(id=school_id).first()
    if role_id:
        user.role = Role.objects(id=role_id).first()
    user.save()

    return RedirectResponse(
        url="/admin/users?message=User%20created%20successfully&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/academics", response_class=HTMLResponse, include_in_schema=False, name="admin_academics")
async def admin_academics(request: Request, current_user: User = Depends(require_admin_user)):
    return templates.TemplateResponse(
        "admin/academics.html",
        admin_context(
            request,
            "Academic Setup",
            current_user=current_user,
            schools=School.objects.order_by("name"),
            years=AcademicYear.objects.order_by("-created_at"),
            classrooms=ClassRoom.objects.order_by("-created_at"),
            sections=Section.objects.order_by("-created_at"),
        ),
    )


@router.post("/academics/year", include_in_schema=False)
async def create_academic_year(
    request: Request,
    current_user: User = Depends(require_admin_user),
    school_id: str = Form(...),
    name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
):
    school = School.objects(id=school_id).first()
    if not school:
        return RedirectResponse(
            url="/admin/academics?message=Select%20a%20valid%20school&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    AcademicYear(
        school=school,
        name=name.strip(),
        start_date=parse_date(start_date),
        end_date=parse_date(end_date),
        is_current=AcademicYear.objects(school=school, is_current=True).count() == 0,
    ).save()

    return RedirectResponse(
        url="/admin/academics?message=Academic%20year%20created&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/academics/classroom", include_in_schema=False)
async def create_classroom(
    request: Request,
    current_user: User = Depends(require_admin_user),
    school_id: str = Form(...),
    academic_year_id: str = Form(...),
    name: str = Form(...),
    numeric_name: str = Form(""),
    class_fee: str = Form("0"),
    section_names: str = Form("A"),
):
    school = School.objects(id=school_id).first()
    academic_year = AcademicYear.objects(id=academic_year_id).first()
    if not school or not academic_year:
        return RedirectResponse(
            url="/admin/academics?message=Provide%20valid%20school%20and%20year&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    sections = [section.strip().upper() for section in section_names.split(",") if section.strip()]
    classroom = ClassRoom(
        school=school,
        academic_year=academic_year,
        name=name.strip(),
        numeric_name=parse_int(numeric_name),
        class_fee=parse_float(class_fee),
        sections=sections,
    ).save()

    for section_name in sections:
        if not Section.objects(classroom=classroom, name=section_name).first():
            Section(
                school=school,
                academic_year=academic_year,
                classroom=classroom,
                name=section_name,
            ).save()

    return RedirectResponse(
        url="/admin/academics?message=Classroom%20created%20with%20sections&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/students", response_class=HTMLResponse, include_in_schema=False, name="admin_students")
async def admin_students(request: Request, branch_code: str = None, current_user: User = Depends(require_admin_user)):
    
    query = Student.objects.order_by("-created_at")
    if branch_code:
       query = query.filter(branch__code=branch_code)
    return templates.TemplateResponse(
        "admin/students.html",
        admin_context(
            request,
            "Students",
            current_user=current_user,
            students=query,
            schools=School.objects.order_by("name"),
            years=AcademicYear.objects.order_by("-created_at"),
            classrooms=ClassRoom.objects.order_by("name"),
            sections=Section.objects.order_by("name"),
        ),
    )


@router.post("/students", include_in_schema=False)
async def create_student(
    request: Request,
    current_user: User = Depends(require_admin_user),
    admission_no: str = Form(...),
    roll_no: str = Form(""),
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    school_id: str = Form(...),
    academic_year_id: str = Form(...),
    classroom_id: str = Form(...),
    section_id: str = Form(...),
):
    if Student.objects(admission_no=admission_no.strip()).first():
        return RedirectResponse(
            url="/admin/students?message=Admission%20number%20already%20exists&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    school = School.objects(id=school_id).first()
    academic_year = AcademicYear.objects(id=academic_year_id).first()
    classroom = ClassRoom.objects(id=classroom_id).first()
    section = Section.objects(id=section_id).first()

    if not all([school, academic_year, classroom, section]):
        return RedirectResponse(
            url="/admin/students?message=Select%20valid%20academic%20references&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    Student(
        admission_no=admission_no.strip(),
        roll_no=roll_no.strip(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender,
        phone=phone.strip(),
        email=email.strip(),
        school=school,
        academic_year=academic_year,
        classroom=classroom,
        section=section,
    ).save()

    return RedirectResponse(
        url="/admin/students?message=Student%20created%20successfully&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/staff", response_class=HTMLResponse, include_in_schema=False, name="admin_staff")
async def admin_staff(request: Request, current_user: User = Depends(require_admin_user)):
    return templates.TemplateResponse(
        "admin/staff.html",
        admin_context(
            request,
            "Staff",
            current_user=current_user,
            staff_members=Staff.objects.order_by("-created_at"),
            schools=School.objects.order_by("name"),
        ),
    )


@router.post("/staff", include_in_schema=False)
async def create_staff(
    request: Request,
    current_user: User = Depends(require_admin_user),
    employee_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(""),
    gender: str = Form(...),
    phone: str = Form(...),
    school_id: str = Form(...),
    designation: str = Form(...),
    staff_type: str = Form(...),
    joining_date: str = Form(...),
    department: str = Form(""),
    basic_salary: str = Form("0"),
):
    if Staff.objects(employee_id=employee_id.strip()).first():
        return RedirectResponse(
            url="/admin/staff?message=Employee%20ID%20already%20exists&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    school = School.objects(id=school_id).first()
    if not school:
        return RedirectResponse(
            url="/admin/staff?message=Select%20a%20valid%20school&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    salary = parse_float(basic_salary)
    Staff(
        employee_id=employee_id.strip(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender,
        phone=phone.strip(),
        school=school,
        designation=designation.strip(),
        staff_type=staff_type,
        joining_date=parse_date(joining_date),
        department=department.strip(),
        basic_salary=salary,
        gross_salary=salary,
    ).save()

    return RedirectResponse(
        url="/admin/staff?message=Staff%20member%20created&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/finance", response_class=HTMLResponse, include_in_schema=False, name="admin_finance")
async def admin_finance(request: Request, current_user: User = Depends(require_admin_user)):
    invoices = FeeInvoice.objects.order_by("-created_at")
    invoice_total = sum(invoice.net_amount or 0 for invoice in invoices)
    balance_total = sum(invoice.balance_amount or 0 for invoice in invoices)
    return templates.TemplateResponse(
        "admin/finance.html",
        admin_context(
            request,
            "Finance",
            current_user=current_user,
            invoices=invoices,
            invoice_total=invoice_total,
            balance_total=balance_total,
            schools=School.objects.order_by("name"),
            years=AcademicYear.objects.order_by("-created_at"),
            students=Student.objects.order_by("first_name"),
        ),
    )


@router.post("/finance/invoices", include_in_schema=False)
async def create_invoice(
    request: Request,
    current_user: User = Depends(require_admin_user),
    school_id: str = Form(...),
    academic_year_id: str = Form(...),
    student_id: str = Form(...),
    invoice_no: str = Form(...),
    due_date: str = Form(...),
    gross_amount: str = Form(...),
    discount_amount: str = Form("0"),
    late_fee: str = Form("0"),
    remarks: str = Form(""),
):
    if FeeInvoice.objects(invoice_no=invoice_no.strip()).first():
        return RedirectResponse(
            url="/admin/finance?message=Invoice%20number%20already%20exists&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    school = School.objects(id=school_id).first()
    academic_year = AcademicYear.objects(id=academic_year_id).first()
    student = Student.objects(id=student_id).first()
    if not all([school, academic_year, student]):
        return RedirectResponse(
            url="/admin/finance?message=Select%20valid%20invoice%20references&type=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    gross = parse_float(gross_amount)
    discount = parse_float(discount_amount)
    late = parse_float(late_fee)
    net = max(gross - discount + late, 0)

    FeeInvoice(
        school=school,
        academic_year=academic_year,
        student=student,
        invoice_no=invoice_no.strip(),
        due_date=parse_date(due_date),
        gross_amount=gross,
        discount_amount=discount,
        late_fee=late,
        net_amount=net,
        balance_amount=net,
        status="Pending",
        remarks=remarks.strip(),
        generated_by=current_user.full_name,
    ).save()

    return RedirectResponse(
        url="/admin/finance?message=Invoice%20created%20successfully&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )

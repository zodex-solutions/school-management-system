from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models.institution import (
    School, AcademicYear, ClassRoom, Section, Subject,
    SubjectMapping, GradingSystem, GradeScale, User, Role, Permission
)
from utils.auth import get_current_user, require_permission
from utils.helpers import success_response, error_response, paginate_query, doc_to_dict

router = APIRouter(prefix="/institution", tags=["Institution"])


# ─── School CRUD ──────────────────────────────────────────────────────────────

class SchoolCreate(BaseModel):
    name: str
    code: str
    tagline: Optional[str] = None
    affiliation_no: Optional[str] = None
    affiliation_board: Optional[str] = None
    established_year: Optional[int] = None
    type: str = "Private"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    currency: str = "INR"
    address: Optional[dict] = None


@router.post("/school")
async def create_school(data: SchoolCreate, current_user: User = Depends(get_current_user)):
    if School.objects(code=data.code).first():
        raise HTTPException(400, "School code already exists")
    school = School(**data.model_dump())
    school.save()
    return success_response({"id": str(school.id), "name": school.name}, "School created successfully")


@router.get("/school")
async def list_schools(current_user: User = Depends(get_current_user)):
    schools = School.objects(is_active=True)
    result = []
    for s in schools:
        result.append({
            "id": str(s.id), "name": s.name, "code": s.code,
            "type": s.type, "affiliation_board": s.affiliation_board,
            "phone": s.phone, "email": s.email, "logo": s.logo
        })
    return success_response(result)


@router.get("/school/{school_id}")
async def get_school(school_id: str, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        return success_response(doc_to_dict(school))
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")


@router.put("/school/{school_id}")
async def update_school(school_id: str, data: dict, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        data.pop('id', None)
        data['updated_at'] = datetime.utcnow()
        school.update(**data)
        return success_response(message="School updated successfully")
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")


# ─── Academic Year ────────────────────────────────────────────────────────────

class AcademicYearCreate(BaseModel):
    school_id: str
    name: str
    start_date: datetime
    end_date: datetime
    is_current: bool = False


@router.post("/academic-year")
async def create_academic_year(data: AcademicYearCreate, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=data.school_id)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")
    
    if data.is_current:
        AcademicYear.objects(school=school, is_current=True).update(is_current=False)
    
    ay = AcademicYear(
        school=school, name=data.name,
        start_date=data.start_date, end_date=data.end_date,
        is_current=data.is_current
    )
    ay.save()
    return success_response({"id": str(ay.id), "name": ay.name}, "Academic year created")


@router.get("/academic-year")
async def list_academic_years(school_id: str, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        years = AcademicYear.objects(school=school, is_active=True).order_by('-start_date')
        result = [{
            "id": str(y.id), "name": y.name,
            "start_date": y.start_date.isoformat() if y.start_date else None,
            "end_date": y.end_date.isoformat() if y.end_date else None,
            "is_current": y.is_current
        } for y in years]
        return success_response(result)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")


@router.patch("/academic-year/{year_id}/set-current")
async def set_current_year(year_id: str, current_user: User = Depends(get_current_user)):
    try:
        ay = AcademicYear.objects.get(id=year_id)
        AcademicYear.objects(school=ay.school, is_current=True).update(is_current=False)
        ay.update(is_current=True)
        return success_response(message="Academic year set as current")
    except AcademicYear.DoesNotExist:
        raise HTTPException(404, "Academic year not found")


# ─── ClassRoom ────────────────────────────────────────────────────────────────

class ClassRoomCreate(BaseModel):
    school_id: str
    academic_year_id: str
    name: str
    numeric_name: Optional[int] = None
    stream_id: Optional[str] = None
    sections: List[str] = []


@router.post("/class")
async def create_class(data: ClassRoomCreate, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=data.school_id)
        ay = AcademicYear.objects.get(id=data.academic_year_id)
    except Exception:
        raise HTTPException(404, "School or Academic Year not found")
    
    classroom = ClassRoom(
        school=school, academic_year=ay,
        name=data.name, numeric_name=data.numeric_name,
        sections=data.sections
    )
    classroom.save()
    
    # Auto-create sections
    for sec_name in data.sections:
        sec = Section(school=school, academic_year=ay, classroom=classroom, name=sec_name)
        sec.save()
    
    return success_response({"id": str(classroom.id), "name": classroom.name}, "Class created successfully")


@router.get("/class")
async def list_classes(
    school_id: str, academic_year_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    try:
        school = School.objects.get(id=school_id)
        query = ClassRoom.objects(school=school, is_active=True)
        if academic_year_id:
            ay = AcademicYear.objects.get(id=academic_year_id)
            query = query.filter(academic_year=ay)
        
        result = []
        for c in query.order_by('numeric_name'):
            sections = Section.objects(classroom=c, is_active=True)
            result.append({
                "id": str(c.id), "name": c.name,
                "numeric_name": c.numeric_name,
                "sections": [{"id": str(s.id), "name": s.name} for s in sections]
            })
        return success_response(result)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")


# ─── Section ──────────────────────────────────────────────────────────────────

@router.get("/section")
async def list_sections(
    classroom_id: str,
    current_user: User = Depends(get_current_user)
):
    try:
        classroom = ClassRoom.objects.get(id=classroom_id)
        sections = Section.objects(classroom=classroom, is_active=True)
        result = [{"id": str(s.id), "name": s.name, "room_number": s.room_number} for s in sections]
        return success_response(result)
    except ClassRoom.DoesNotExist:
        raise HTTPException(404, "Class not found")


# ─── Subject CRUD ─────────────────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    school_id: str
    name: str
    code: str
    description: Optional[str] = None
    subject_type: str = "Theory"
    max_theory_marks: float = 100
    max_practical_marks: float = 0
    passing_marks: float = 33
    is_optional: bool = False


@router.post("/subject")
async def create_subject(data: SubjectCreate, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=data.school_id)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")
    
    if Subject.objects(school=school, code=data.code).first():
        raise HTTPException(400, "Subject code already exists")
    
    subject = Subject(school=school, **{k: v for k, v in data.model_dump().items() if k != 'school_id'})
    subject.save()
    return success_response({"id": str(subject.id), "name": subject.name}, "Subject created")


@router.get("/subject")
async def list_subjects(school_id: str, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        subjects = Subject.objects(school=school, is_active=True).order_by('name')
        result = [{
            "id": str(s.id), "name": s.name, "code": s.code,
            "subject_type": s.subject_type, "max_theory_marks": s.max_theory_marks,
            "max_practical_marks": s.max_practical_marks, "passing_marks": s.passing_marks,
            "is_optional": s.is_optional
        } for s in subjects]
        return success_response(result)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")


@router.put("/subject/{subject_id}")
async def update_subject(subject_id: str, data: dict, current_user: User = Depends(get_current_user)):
    try:
        subject = Subject.objects.get(id=subject_id)
        data.pop('id', None)
        subject.update(**data)
        return success_response(message="Subject updated")
    except Subject.DoesNotExist:
        raise HTTPException(404, "Subject not found")


@router.delete("/subject/{subject_id}")
async def delete_subject(subject_id: str, current_user: User = Depends(get_current_user)):
    try:
        subject = Subject.objects.get(id=subject_id)
        subject.update(is_active=False)
        return success_response(message="Subject deleted")
    except Subject.DoesNotExist:
        raise HTTPException(404, "Subject not found")


# ─── Grading System ───────────────────────────────────────────────────────────

@router.post("/grading-system")
async def create_grading_system(data: dict, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=data['school_id'])
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")
    
    if data.get('is_default'):
        GradingSystem.objects(school=school, is_default=True).update(is_default=False)
    
    gs = GradingSystem(
        school=school,
        name=data['name'],
        grading_type=data.get('grading_type', 'Marks'),
        is_default=data.get('is_default', False)
    )
    
    for scale in data.get('scales', []):
        gs.scales.append(GradeScale(**scale))
    
    gs.save()
    return success_response({"id": str(gs.id)}, "Grading system created")


@router.get("/grading-system")
async def list_grading_systems(school_id: str, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        systems = GradingSystem.objects(school=school, is_active=True)
        result = []
        for gs in systems:
            result.append({
                "id": str(gs.id), "name": gs.name,
                "grading_type": gs.grading_type,
                "is_default": gs.is_default,
                "scales": [{"grade": s.grade, "min": s.min_marks, "max": s.max_marks, "gp": s.grade_point} for s in gs.scales]
            })
        return success_response(result)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@router.get("/dashboard/{school_id}")
async def get_dashboard_stats(school_id: str, current_user: User = Depends(get_current_user)):
    from models.student import Student
    from models.staff import Staff
    from models.fees import FeeInvoice
    from models.attendance import StudentAttendance
    
    try:
        school = School.objects.get(id=school_id)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            "total_students": Student.objects(school=school, is_active=True).count(),
            "total_staff": Staff.objects(school=school, is_active=True).count(),
            "total_classes": ClassRoom.objects(school=school, is_active=True).count(),
            "pending_fees": FeeInvoice.objects(school=school, status__in=["Pending", "Partial", "Overdue"]).count(),
            "today_student_attendance": StudentAttendance.objects(school=school, date=today).count(),
        }
        return success_response(stats)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")

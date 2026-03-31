from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.examination import Exam, MarksEntry, Result, SubjectResult
from models.academic import Timetable, Homework, StudyMaterial, LessonPlan, Syllabus, OnlineClass, TimetableDay, TimetablePeriod
from models.institution import School, AcademicYear, ClassRoom, Section, Subject, User
from models.student import Student
from models.staff import Staff
from utils.auth import get_current_user
from utils.helpers import success_response

exam_router = APIRouter(prefix="/exams", tags=["Examinations"])
academic_router = APIRouter(prefix="/academics", tags=["Academic Management"])


# ═══════════════════════════════════════════════════════════════════════════════
#  EXAMINATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class ExamCreate(BaseModel):
    school_id: str
    academic_year_id: str
    name: str
    exam_type: str
    classroom_ids: List[str] = []
    section_ids: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    schedule: List[dict] = []


@exam_router.post("")
async def create_exam(data: ExamCreate, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data.school_id)
    ay = AcademicYear.objects.get(id=data.academic_year_id)
    
    exam = Exam(
        school=school, academic_year=ay,
        name=data.name, exam_type=data.exam_type,
        start_date=data.start_date, end_date=data.end_date,
        created_by=current_user.full_name
    )
    
    for cid in data.classroom_ids:
        try:
            exam.classrooms.append(ClassRoom.objects.get(id=cid))
        except ClassRoom.DoesNotExist:
            pass
    
    for sid in data.section_ids:
        try:
            exam.sections.append(Section.objects.get(id=sid))
        except Section.DoesNotExist:
            pass
    
    exam.save()
    return success_response({"id": str(exam.id), "name": exam.name}, "Exam created successfully")


@exam_router.get("")
async def list_exams(
    school_id: str,
    academic_year_id: Optional[str] = None,
    exam_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = Exam.objects(school=school, is_active=True)
    if academic_year_id:
        ay = AcademicYear.objects.get(id=academic_year_id)
        query = query.filter(academic_year=ay)
    if exam_type:
        query = query.filter(exam_type=exam_type)
    if status:
        query = query.filter(status=status)
    
    result = [{
        "id": str(e.id), "name": e.name,
        "exam_type": e.exam_type, "status": e.status,
        "start_date": e.start_date.isoformat() if e.start_date else None,
        "end_date": e.end_date.isoformat() if e.end_date else None,
        "classes": [c.name for c in e.classrooms]
    } for e in query.order_by('-created_at')]
    return success_response(result)


@exam_router.patch("/{exam_id}/status")
async def update_exam_status(
    exam_id: str, status: str,
    current_user: User = Depends(get_current_user)
):
    valid_statuses = ["Draft", "Scheduled", "Ongoing", "Completed", "Results Published"]
    if status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    try:
        exam = Exam.objects.get(id=exam_id)
        exam.update(status=status, updated_at=datetime.utcnow())
        return success_response(message=f"Exam status updated to {status}")
    except Exam.DoesNotExist:
        raise HTTPException(404, "Exam not found")


# ─── Marks Entry ──────────────────────────────────────────────────────────────

class MarksBulkEntry(BaseModel):
    school_id: str
    exam_id: str
    classroom_id: str
    section_id: str
    subject_id: str
    entries: List[dict]  # [{student_id, theory_marks, practical_marks, is_absent}]


@exam_router.post("/marks/bulk")
async def enter_marks_bulk(data: MarksBulkEntry, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data.school_id)
    exam = Exam.objects.get(id=data.exam_id)
    classroom = ClassRoom.objects.get(id=data.classroom_id)
    section = Section.objects.get(id=data.section_id)
    subject = Subject.objects.get(id=data.subject_id)
    
    saved = 0
    for entry in data.entries:
        try:
            student = Student.objects.get(id=entry['student_id'])
            theory = entry.get('theory_marks', 0)
            practical = entry.get('practical_marks', 0)
            total = theory + practical
            
            existing = MarksEntry.objects(exam=exam, student=student, subject=subject).first()
            if existing:
                existing.update(
                    theory_marks=theory, practical_marks=practical,
                    total_marks=total, is_absent=entry.get('is_absent', False),
                    entered_by=current_user.full_name, entered_at=datetime.utcnow()
                )
            else:
                me = MarksEntry(
                    school=school, exam=exam, student=student,
                    subject=subject, classroom=classroom, section=section,
                    theory_marks=theory, practical_marks=practical,
                    total_marks=total, max_marks=subject.max_theory_marks + subject.max_practical_marks,
                    is_absent=entry.get('is_absent', False),
                    entered_by=current_user.full_name
                )
                me.save()
            saved += 1
        except Exception:
            continue
    
    return success_response({"saved": saved}, f"Marks saved for {saved} students")


@exam_router.get("/marks")
async def get_marks(
    exam_id: str,
    classroom_id: Optional[str] = None,
    section_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    student_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    exam = Exam.objects.get(id=exam_id)
    query = MarksEntry.objects(exam=exam)
    
    if classroom_id:
        query = query.filter(classroom=ClassRoom.objects.get(id=classroom_id))
    if section_id:
        query = query.filter(section=Section.objects.get(id=section_id))
    if subject_id:
        query = query.filter(subject=Subject.objects.get(id=subject_id))
    if student_id:
        query = query.filter(student=Student.objects.get(id=student_id))
    
    result = [{
        "id": str(m.id),
        "student_name": m.student.full_name if m.student else None,
        "student_id": str(m.student.id) if m.student else None,
        "subject_name": m.subject.name if m.subject else None,
        "theory_marks": m.theory_marks,
        "practical_marks": m.practical_marks,
        "total_marks": m.total_marks,
        "max_marks": m.max_marks,
        "is_absent": m.is_absent
    } for m in query]
    return success_response(result)


@exam_router.post("/{exam_id}/generate-results")
async def generate_results(
    exam_id: str,
    classroom_id: str,
    section_id: str,
    current_user: User = Depends(get_current_user)
):
    """Auto-generate results from marks entries"""
    exam = Exam.objects.get(id=exam_id)
    classroom = ClassRoom.objects.get(id=classroom_id)
    section = Section.objects.get(id=section_id)
    
    students = Student.objects(classroom=classroom, section=section, is_active=True)
    results_generated = 0
    
    for student in students:
        marks = MarksEntry.objects(exam=exam, student=student)
        if not marks:
            continue
        
        subject_results = []
        total_max = 0
        total_obtained = 0
        
        for m in marks:
            pct = (m.total_marks / m.max_marks * 100) if m.max_marks and not m.is_absent else 0
            grade, gp = calculate_grade(pct)
            is_pass = m.total_marks >= (m.subject.passing_marks if m.subject else 33) and not m.is_absent
            
            sr = SubjectResult(
                subject=m.subject,
                subject_name=m.subject.name if m.subject else "",
                subject_code=m.subject.code if m.subject else "",
                max_marks=m.max_marks,
                theory_marks=m.theory_marks,
                practical_marks=m.practical_marks,
                total_marks=m.total_marks if not m.is_absent else 0,
                percentage=round(pct, 2),
                grade=grade,
                grade_point=gp,
                is_absent=m.is_absent,
                is_pass=is_pass
            )
            subject_results.append(sr)
            total_max += m.max_marks or 0
            total_obtained += m.total_marks or 0
        
        overall_pct = (total_obtained / total_max * 100) if total_max > 0 else 0
        overall_grade, overall_gp = calculate_grade(overall_pct)
        overall_pass = all(sr.is_pass for sr in subject_results)
        
        existing_result = Result.objects(exam=exam, student=student).first()
        result_data = dict(
            school=student.school,
            academic_year=student.academic_year,
            exam=exam, student=student,
            classroom=classroom, section=section,
            subject_results=subject_results,
            total_max_marks=total_max,
            total_obtained_marks=total_obtained,
            percentage=round(overall_pct, 2),
            cgpa=round(overall_gp, 2),
            overall_grade=overall_grade,
            is_pass=overall_pass,
            result_status="Pass" if overall_pass else "Fail"
        )
        
        if existing_result:
            existing_result.update(**result_data)
        else:
            Result(**result_data).save()
        
        results_generated += 1
    
    # Calculate ranks
    results = list(Result.objects(exam=exam, classroom=classroom, section=section).order_by('-percentage'))
    for rank, result in enumerate(results, 1):
        result.update(rank_in_section=rank)
    
    return success_response({"generated": results_generated}, "Results generated successfully")


def calculate_grade(percentage: float):
    """Returns (grade, grade_point)"""
    if percentage >= 91:
        return "A+", 10.0
    elif percentage >= 81:
        return "A", 9.0
    elif percentage >= 71:
        return "B+", 8.0
    elif percentage >= 61:
        return "B", 7.0
    elif percentage >= 51:
        return "C+", 6.0
    elif percentage >= 41:
        return "C", 5.0
    elif percentage >= 33:
        return "D", 4.0
    else:
        return "F", 0.0


@exam_router.get("/results")
async def get_results(
    exam_id: str,
    classroom_id: Optional[str] = None,
    section_id: Optional[str] = None,
    student_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    exam = Exam.objects.get(id=exam_id)
    query = Result.objects(exam=exam)
    if classroom_id:
        query = query.filter(classroom=ClassRoom.objects.get(id=classroom_id))
    if section_id:
        query = query.filter(section=Section.objects.get(id=section_id))
    if student_id:
        query = query.filter(student=Student.objects.get(id=student_id))
    
    result = [{
        "id": str(r.id),
        "student_name": r.student.full_name if r.student else None,
        "roll_no": r.student.roll_no if r.student else None,
        "total_obtained": r.total_obtained_marks,
        "total_max": r.total_max_marks,
        "percentage": r.percentage,
        "grade": r.overall_grade,
        "cgpa": r.cgpa,
        "rank": r.rank_in_section,
        "result_status": r.result_status,
        "is_pass": r.is_pass,
        "subjects": [{
            "name": s.subject_name,
            "obtained": s.total_marks,
            "max": s.max_marks,
            "grade": s.grade,
            "is_pass": s.is_pass
        } for s in r.subject_results]
    } for r in query.order_by('rank_in_section')]
    return success_response(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  ACADEMIC MANAGEMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@academic_router.post("/timetable")
async def create_timetable(data: dict, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data['school_id'])
    ay = AcademicYear.objects.get(id=data['academic_year_id'])
    classroom = ClassRoom.objects.get(id=data['classroom_id'])
    section = Section.objects.get(id=data['section_id'])
    
    tt = Timetable(
        school=school, academic_year=ay,
        classroom=classroom, section=section,
        name=data.get('name', 'Regular Timetable'),
        created_by=current_user.full_name
    )
    
    for day_data in data.get('days', []):
        day = TimetableDay(day=day_data['day'])
        for p in day_data.get('periods', []):
            period = TimetablePeriod(
                period_no=p['period_no'],
                start_time=p['start_time'],
                end_time=p['end_time'],
                room=p.get('room'),
                is_break=p.get('is_break', False),
                break_name=p.get('break_name')
            )
            if p.get('subject_id'):
                try:
                    period.subject = Subject.objects.get(id=p['subject_id'])
                except Subject.DoesNotExist:
                    pass
            if p.get('teacher_id'):
                try:
                    period.teacher = Staff.objects.get(id=p['teacher_id'])
                except Staff.DoesNotExist:
                    pass
            day.periods.append(period)
        tt.days.append(day)
    
    tt.save()
    return success_response({"id": str(tt.id)}, "Timetable created")


@academic_router.get("/timetable")
async def get_timetable(
    school_id: str, classroom_id: str, section_id: str,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    classroom = ClassRoom.objects.get(id=classroom_id)
    section = Section.objects.get(id=section_id)
    
    tt = Timetable.objects(school=school, classroom=classroom, section=section, is_active=True).first()
    if not tt:
        return success_response(None, "No timetable found")
    
    days_data = []
    for d in tt.days:
        periods_data = []
        for p in d.periods:
            periods_data.append({
                "period_no": p.period_no,
                "start_time": p.start_time,
                "end_time": p.end_time,
                "subject": p.subject.name if p.subject else None,
                "teacher": p.teacher.full_name if p.teacher else None,
                "room": p.room,
                "is_break": p.is_break,
                "break_name": p.break_name
            })
        days_data.append({"day": d.day, "periods": periods_data})
    
    return success_response({"id": str(tt.id), "name": tt.name, "days": days_data})


@academic_router.post("/homework")
async def create_homework(data: dict, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data['school_id'])
    ay = AcademicYear.objects.get(id=data['academic_year_id'])
    teacher = Staff.objects.get(id=data['teacher_id'])
    classroom = ClassRoom.objects.get(id=data['classroom_id'])
    subject = Subject.objects.get(id=data['subject_id'])
    
    hw = Homework(
        school=school, academic_year=ay,
        teacher=teacher, classroom=classroom,
        subject=subject,
        title=data['title'],
        description=data['description'],
        due_date=datetime.fromisoformat(data['due_date']),
        max_marks=data.get('max_marks', 10)
    )
    if data.get('section_id'):
        hw.section = Section.objects.get(id=data['section_id'])
    hw.save()
    return success_response({"id": str(hw.id)}, "Homework assigned")


@academic_router.get("/homework")
async def list_homework(
    school_id: str,
    classroom_id: Optional[str] = None,
    teacher_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = Homework.objects(school=school, is_active=True)
    if classroom_id:
        query = query.filter(classroom=ClassRoom.objects.get(id=classroom_id))
    if teacher_id:
        query = query.filter(teacher=Staff.objects.get(id=teacher_id))
    
    result = [{
        "id": str(h.id),
        "title": h.title,
        "description": h.description,
        "subject": h.subject.name if h.subject else None,
        "classroom": h.classroom.name if h.classroom else None,
        "section": h.section.name if h.section else None,
        "assigned_date": h.assigned_date.isoformat() if h.assigned_date else None,
        "due_date": h.due_date.isoformat() if h.due_date else None,
        "max_marks": h.max_marks,
        "teacher": h.teacher.full_name if h.teacher else None,
        "submission_count": len(h.submissions)
    } for h in query.order_by('-assigned_date')]
    return success_response(result)


@academic_router.post("/study-material")
async def upload_material(data: dict, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data['school_id'])
    ay = AcademicYear.objects.get(id=data['academic_year_id'])
    teacher = Staff.objects.get(id=data['teacher_id'])
    classroom = ClassRoom.objects.get(id=data['classroom_id'])
    subject = Subject.objects.get(id=data['subject_id'])
    
    mat = StudyMaterial(
        school=school, academic_year=ay, teacher=teacher,
        classroom=classroom, subject=subject,
        title=data['title'], description=data.get('description'),
        material_type=data.get('material_type', 'Notes'),
        file_path=data.get('file_path'),
        external_link=data.get('external_link')
    )
    mat.save()
    return success_response({"id": str(mat.id)}, "Study material added")


@academic_router.get("/study-material")
async def list_materials(
    school_id: str, classroom_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = StudyMaterial.objects(school=school, is_visible=True)
    if classroom_id:
        query = query.filter(classroom=ClassRoom.objects.get(id=classroom_id))
    if subject_id:
        query = query.filter(subject=Subject.objects.get(id=subject_id))
    
    result = [{
        "id": str(m.id), "title": m.title,
        "description": m.description,
        "material_type": m.material_type,
        "subject": m.subject.name if m.subject else None,
        "teacher": m.teacher.full_name if m.teacher else None,
        "file_path": m.file_path,
        "external_link": m.external_link,
        "upload_date": m.upload_date.isoformat() if m.upload_date else None
    } for m in query.order_by('-upload_date')]
    return success_response(result)


@academic_router.post("/online-class")
async def schedule_online_class(data: dict, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data['school_id'])
    teacher = Staff.objects.get(id=data['teacher_id'])
    classroom = ClassRoom.objects.get(id=data['classroom_id'])
    subject = Subject.objects.get(id=data['subject_id'])
    
    oc = OnlineClass(
        school=school, teacher=teacher,
        classroom=classroom, subject=subject,
        title=data['title'],
        description=data.get('description'),
        platform=data.get('platform', 'Google Meet'),
        meeting_link=data.get('meeting_link'),
        meeting_id=data.get('meeting_id'),
        meeting_password=data.get('meeting_password'),
        scheduled_at=datetime.fromisoformat(data['scheduled_at']),
        duration_minutes=data.get('duration_minutes', 45)
    )
    oc.save()
    return success_response({"id": str(oc.id)}, "Online class scheduled")


@academic_router.get("/online-class")
async def list_online_classes(
    school_id: str, classroom_id: Optional[str] = None,
    upcoming_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = OnlineClass.objects(school=school)
    if classroom_id:
        query = query.filter(classroom=ClassRoom.objects.get(id=classroom_id))
    if upcoming_only:
        query = query.filter(scheduled_at__gte=datetime.utcnow(), status="Scheduled")
    
    result = [{
        "id": str(c.id), "title": c.title,
        "subject": c.subject.name if c.subject else None,
        "teacher": c.teacher.full_name if c.teacher else None,
        "platform": c.platform,
        "meeting_link": c.meeting_link,
        "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
        "duration_minutes": c.duration_minutes,
        "status": c.status
    } for c in query.order_by('-scheduled_at')]
    return success_response(result)

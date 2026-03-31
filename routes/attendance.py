from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from models.attendance import StudentAttendance, StaffAttendance, Holiday, AttendanceSummary, StudentAttendanceRecord, StaffAttendanceRecord
from models.institution import School, AcademicYear, ClassRoom, Section, Subject, User
from models.student import Student
from models.staff import Staff
from utils.auth import get_current_user
from utils.helpers import success_response

router = APIRouter(prefix="/attendance", tags=["Attendance"])


class AttendanceRecord(BaseModel):
    student_id: str
    status: str  # Present, Absent, Late, Excused
    remarks: Optional[str] = None
    check_in_time: Optional[str] = None


class MarkStudentAttendance(BaseModel):
    school_id: str
    academic_year_id: str
    classroom_id: str
    section_id: str
    date: datetime
    subject_id: Optional[str] = None
    period_no: Optional[int] = None
    attendance_type: str = "Daily"
    records: List[AttendanceRecord]


@router.post("/student/mark")
async def mark_student_attendance(
    data: MarkStudentAttendance,
    current_user: User = Depends(get_current_user)
):
    try:
        school = School.objects.get(id=data.school_id)
        ay = AcademicYear.objects.get(id=data.academic_year_id)
        classroom = ClassRoom.objects.get(id=data.classroom_id)
        section = Section.objects.get(id=data.section_id)
    except Exception as e:
        raise HTTPException(404, f"Reference not found: {str(e)}")
    
    att_date = data.date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check if already marked
    existing = StudentAttendance.objects(
        school=school, classroom=classroom, section=section,
        date=att_date, period_no=data.period_no
    ).first()
    
    records = []
    present_count = 0
    absent_count = 0
    late_count = 0
    
    for rec in data.records:
        try:
            student = Student.objects.get(id=rec.student_id)
            record = StudentAttendanceRecord(
                student=student,
                student_name=student.full_name,
                roll_no=student.roll_no,
                status=rec.status,
                remarks=rec.remarks,
                check_in_time=rec.check_in_time
            )
            records.append(record)
            if rec.status == "Present":
                present_count += 1
            elif rec.status == "Absent":
                absent_count += 1
            elif rec.status == "Late":
                late_count += 1
        except Student.DoesNotExist:
            continue
    
    if existing:
        existing.records = records
        existing.present_count = present_count
        existing.absent_count = absent_count
        existing.late_count = late_count
        existing.marked_by = current_user.full_name
        existing.marked_at = datetime.utcnow()
        existing.save()
        attendance = existing
    else:
        subject = None
        if data.subject_id:
            try:
                subject = Subject.objects.get(id=data.subject_id)
            except Subject.DoesNotExist:
                pass
        
        attendance = StudentAttendance(
            school=school, academic_year=ay,
            classroom=classroom, section=section,
            subject=subject,
            date=att_date, period_no=data.period_no,
            attendance_type=data.attendance_type,
            records=records,
            total_students=len(records),
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            marked_by=current_user.full_name
        )
        attendance.save()
    
    return success_response({
        "id": str(attendance.id),
        "total": len(records),
        "present": present_count,
        "absent": absent_count,
        "late": late_count
    }, "Attendance marked successfully")


@router.get("/student")
async def get_student_attendance(
    school_id: str,
    classroom_id: str,
    section_id: str,
    date: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    classroom = ClassRoom.objects.get(id=classroom_id)
    section = Section.objects.get(id=section_id)
    
    query = StudentAttendance.objects(school=school, classroom=classroom, section=section)
    
    if date:
        dt = datetime.fromisoformat(date).replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(date=dt)
    elif from_date and to_date:
        fd = datetime.fromisoformat(from_date)
        td = datetime.fromisoformat(to_date)
        query = query.filter(date__gte=fd, date__lte=td)
    
    result = []
    for att in query.order_by('-date'):
        records = [{
            "student_id": str(r.student.id) if r.student else None,
            "student_name": r.student_name,
            "roll_no": r.roll_no,
            "status": r.status,
            "remarks": r.remarks,
            "check_in_time": r.check_in_time
        } for r in att.records]
        
        result.append({
            "id": str(att.id),
            "date": att.date.isoformat(),
            "attendance_type": att.attendance_type,
            "total_students": att.total_students,
            "present_count": att.present_count,
            "absent_count": att.absent_count,
            "late_count": att.late_count,
            "records": records,
            "marked_by": att.marked_by,
            "marked_at": att.marked_at.isoformat() if att.marked_at else None
        })
    
    return success_response(result)


@router.get("/student/report/{student_id}")
async def get_student_attendance_report(
    student_id: str,
    academic_year_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")
    
    # Get all attendance for this student
    query = StudentAttendance.objects(
        school=student.school,
        classroom=student.classroom,
        section=student.section
    )
    
    if month and year:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        query = query.filter(date__gte=start, date__lt=end)
    
    total_days = 0
    present_days = 0
    absent_days = 0
    late_days = 0
    daily_records = []
    
    for att in query.order_by('date'):
        for rec in att.records:
            if rec.student and str(rec.student.id) == student_id:
                total_days += 1
                if rec.status == "Present":
                    present_days += 1
                elif rec.status == "Absent":
                    absent_days += 1
                elif rec.status == "Late":
                    late_days += 1
                    present_days += 1  # Late counts as present
                
                daily_records.append({
                    "date": att.date.isoformat(),
                    "status": rec.status,
                    "remarks": rec.remarks
                })
                break
    
    attendance_pct = (present_days / total_days * 100) if total_days > 0 else 0
    
    return success_response({
        "student_id": student_id,
        "student_name": student.full_name,
        "total_working_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "attendance_percentage": round(attendance_pct, 2),
        "daily_records": daily_records
    })


# ─── Staff Attendance ─────────────────────────────────────────────────────────

class StaffAttRecord(BaseModel):
    staff_id: str
    status: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    remarks: Optional[str] = None


class MarkStaffAttendance(BaseModel):
    school_id: str
    date: datetime
    records: List[StaffAttRecord]


@router.post("/staff/mark")
async def mark_staff_attendance(
    data: MarkStaffAttendance,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=data.school_id)
    att_date = data.date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    existing = StaffAttendance.objects(school=school, date=att_date).first()
    
    records = []
    present_count = absent_count = on_leave_count = 0
    
    for rec in data.records:
        try:
            staff = Staff.objects.get(id=rec.staff_id)
            record = StaffAttendanceRecord(
                staff=staff, status=rec.status,
                check_in_time=rec.check_in_time,
                check_out_time=rec.check_out_time,
                remarks=rec.remarks
            )
            records.append(record)
            if rec.status == "Present":
                present_count += 1
            elif rec.status == "Absent":
                absent_count += 1
            elif rec.status == "On-Leave":
                on_leave_count += 1
        except Staff.DoesNotExist:
            continue
    
    if existing:
        existing.records = records
        existing.present_count = present_count
        existing.absent_count = absent_count
        existing.on_leave_count = on_leave_count
        existing.marked_by = current_user.full_name
        existing.save()
    else:
        att = StaffAttendance(
            school=school, date=att_date,
            records=records, total_staff=len(records),
            present_count=present_count,
            absent_count=absent_count,
            on_leave_count=on_leave_count,
            marked_by=current_user.full_name
        )
        att.save()
    
    return success_response({
        "total": len(records),
        "present": present_count,
        "absent": absent_count,
        "on_leave": on_leave_count
    }, "Staff attendance marked")


# ─── Holidays ─────────────────────────────────────────────────────────────────

@router.post("/holiday")
async def add_holiday(data: dict, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data['school_id'])
    ay = AcademicYear.objects.get(id=data['academic_year_id'])
    holiday = Holiday(
        school=school, academic_year=ay,
        name=data['name'],
        date=datetime.fromisoformat(data['date']),
        holiday_type=data.get('holiday_type', 'School'),
        description=data.get('description')
    )
    holiday.save()
    return success_response({"id": str(holiday.id)}, "Holiday added")


@router.get("/holiday")
async def list_holidays(
    school_id: str, academic_year_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = Holiday.objects(school=school, is_active=True)
    if academic_year_id:
        ay = AcademicYear.objects.get(id=academic_year_id)
        query = query.filter(academic_year=ay)
    result = [{
        "id": str(h.id), "name": h.name,
        "date": h.date.isoformat(),
        "holiday_type": h.holiday_type,
        "description": h.description
    } for h in query.order_by('date')]
    return success_response(result)

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.student import Student, TransferCertificate
from models.institution import School, AcademicYear, ClassRoom, Section, User
from models.transport import TransportRoute, StudentTransport, Vehicle
from models.attendance import StudentAttendance
from models.fees import FeeInvoice, PaymentTransaction
from models.examination import Result
from utils.auth import get_current_user
from utils.helpers import (
    success_response, paginate_query, generate_admission_no,
    generate_id, generate_tc_no, save_upload_file, doc_to_dict
)

router = APIRouter(prefix="/students", tags=["Students"])


# ─── Admission ────────────────────────────────────────────────────────────────

class StudentAdmission(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: str
    religion: Optional[str] = None
    caste: Optional[str] = None
    nationality: str = "Indian"
    aadhar_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    current_address_details: Optional[dict] = None
    permanent_address_details: Optional[dict] = None
    school_id: str
    academic_year_id: str
    classroom_id: str
    section_id: str
    branch_code: Optional[str] = None
    branch_name: Optional[str] = None
    admission_date: Optional[datetime] = None
    admission_type: str = "New"
    registration_type: str = "Manual"
    parent_info: Optional[dict] = None
    medical_info: Optional[dict] = None
    previous_school: Optional[dict] = None
    uses_transport: bool = False
    transport_route_id: Optional[str] = None
    transport_area: Optional[str] = None
    bus_stop: Optional[str] = None
    bus_no: Optional[str] = None
    transport_months: List[str] = []
    migration: bool = False
    lateral_entry: bool = False
    in_hostel: bool = False
    extra_activities: List[str] = []
    remarks: Optional[str] = None
    referral_type: Optional[str] = None
    referral_number: Optional[str] = None
    referral_email: Optional[str] = None


def _normalize_address_text(address: Optional[dict], fallback: Optional[str] = None) -> Optional[str]:
    if fallback:
        return fallback
    if not address:
        return None
    parts = [address.get(key) for key in ["address", "village_area", "post_office", "city", "state", "pin_code"]]
    return ", ".join([part for part in parts if part])


def _sync_student_transport(student: Student, route_id: Optional[str], payload: StudentAdmission):
    StudentTransport.objects(student=student, is_active=True).update(is_active=False)
    if not (payload.uses_transport and route_id):
        student.update(
            uses_transport=False,
            transport_route=None,
            transport_route_name=None,
            transport_fee_per_month=0
        )
        return None

    route = TransportRoute.objects.get(id=route_id)
    vehicle = Vehicle.objects(route=route, is_active=True).first()
    assignment = StudentTransport(
        school=student.school,
        student=student,
        route=route,
        vehicle=vehicle,
        pickup_stop=payload.bus_stop,
        drop_stop=payload.bus_stop,
        pickup_time=route.morning_departure,
        drop_time=route.afternoon_departure,
        academic_year=student.academic_year.name if student.academic_year else None,
        fee_per_month=route.fee_per_month
    )
    assignment.save()
    student.update(
        uses_transport=True,
        transport_route=str(route.id),
        transport_route_name=route.route_name,
        transport_area=payload.transport_area,
        bus_stop=payload.bus_stop,
        bus_no=payload.bus_no or (vehicle.vehicle_no if vehicle else None),
        transport_fee_per_month=route.fee_per_month,
        transport_months=payload.transport_months or []
    )
    return route


@router.post("")
async def admit_student(data: StudentAdmission, current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=data.school_id)
        ay = AcademicYear.objects.get(id=data.academic_year_id)
        classroom = ClassRoom.objects.get(id=data.classroom_id)
        section = Section.objects.get(id=data.section_id)
    except Exception as e:
        raise HTTPException(404, f"Reference not found: {str(e)}")
    
    admission_no = generate_admission_no(school.code)
    student_id = generate_id("STU")
    
    student = Student(
        admission_no=admission_no,
        student_id=student_id,
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        religion=data.religion,
        caste=data.caste,
        nationality=data.nationality,
        aadhar_number=data.aadhar_number,
        phone=data.phone,
        email=data.email,
        current_address=_normalize_address_text(data.current_address_details, data.current_address),
        permanent_address=_normalize_address_text(data.permanent_address_details, data.permanent_address),
        current_address_details=data.current_address_details,
        permanent_address_details=data.permanent_address_details,
        school=school,
        academic_year=ay,
        classroom=classroom,
        section=section,
        branch_code=data.branch_code,
        branch_name=data.branch_name,
        admission_date=data.admission_date or datetime.utcnow(),
        admission_type=data.admission_type,
        registration_type=data.registration_type,
        uses_transport=data.uses_transport,
        transport_area=data.transport_area,
        bus_stop=data.bus_stop,
        bus_no=data.bus_no,
        transport_months=data.transport_months,
        migration=data.migration,
        lateral_entry=data.lateral_entry,
        in_hostel=data.in_hostel,
        extra_activities=data.extra_activities,
        remarks=data.remarks,
        referral_type=data.referral_type,
        referral_number=data.referral_number,
        referral_email=data.referral_email
    )
    
    if data.parent_info:
        from models.student import ParentInfo
        student.parent_info = ParentInfo(**data.parent_info)
    
    if data.medical_info:
        from models.student import MedicalInfo
        student.medical_info = MedicalInfo(**data.medical_info)
    
    student.save()
    route = None
    if data.transport_route_id:
        route = _sync_student_transport(student, data.transport_route_id, data)
        student.reload()
    
    return success_response({
        "id": str(student.id),
        "admission_no": student.admission_no,
        "student_id": student.student_id,
        "full_name": student.full_name,
        "transport_route_name": route.route_name if route else None
    }, "Student admitted successfully")


@router.get("")
async def list_students(
    school_id: str,
    academic_year_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    section_id: Optional[str] = None,
    branch_code: Optional[str] = None,
    admission_status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    try:
        school = School.objects.get(id=school_id)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")
    
    query = Student.objects(school=school, is_active=True)
    
    if academic_year_id:
        try:
            ay = AcademicYear.objects.get(id=academic_year_id)
            query = query.filter(academic_year=ay)
        except AcademicYear.DoesNotExist:
            pass
    
    if classroom_id:
        try:
            classroom = ClassRoom.objects.get(id=classroom_id)
            query = query.filter(classroom=classroom)
        except ClassRoom.DoesNotExist:
            pass
    
    if section_id:
        try:
            section = Section.objects.get(id=section_id)
            query = query.filter(section=section)
        except Section.DoesNotExist:
            pass

    if branch_code:
        query = query.filter(branch_code=branch_code)
    
    if admission_status:
        query = query.filter(admission_status=admission_status)
    
    if search:
        import re
        pattern = re.compile(search, re.IGNORECASE)
        query = query.filter(
            __raw__={"$or": [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"admission_no": {"$regex": search, "$options": "i"}},
                {"student_id": {"$regex": search, "$options": "i"}}
            ]}
        )
    
    total = query.count()
    students = query.order_by('first_name').skip((page - 1) * per_page).limit(per_page)
    
    result = []
    for s in students:
        result.append({
            "id": str(s.id),
            "admission_no": s.admission_no,
            "student_id": s.student_id,
            "full_name": s.full_name,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "gender": s.gender,
            "date_of_birth": s.date_of_birth.isoformat() if s.date_of_birth else None,
            "classroom": s.classroom.name if s.classroom else None,
            "section": s.section.name if s.section else None,
            "branch_name": s.branch_name,
            "admission_status": s.admission_status,
            "phone": s.phone,
            "photo": s.photo,
            "father_name": s.parent_info.father_name if s.parent_info else None,
            "father_phone": s.parent_info.father_phone if s.parent_info else None,
            "route_name": s.transport_route_name,
        })
    
    return success_response(result, meta={
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    })


@router.get("/{student_id}")
async def get_student(student_id: str, current_user: User = Depends(get_current_user)):
    try:
        student = Student.objects.get(id=student_id)
        data = {
            "id": str(student.id),
            "admission_no": student.admission_no,
            "student_id": student.student_id,
            "full_name": student.full_name,
            "first_name": student.first_name,
            "middle_name": student.middle_name,
            "last_name": student.last_name,
            "gender": student.gender,
            "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
            "religion": student.religion,
            "caste": student.caste,
            "nationality": student.nationality,
            "aadhar_number": student.aadhar_number,
            "phone": student.phone,
            "email": student.email,
            "current_address": student.current_address,
            "permanent_address": student.permanent_address,
            "current_address_details": student.current_address_details or {},
            "permanent_address_details": student.permanent_address_details or {},
            "photo": student.photo,
            "branch_code": student.branch_code,
            "branch_name": student.branch_name,
            "classroom_id": str(student.classroom.id) if student.classroom else None,
            "classroom_name": student.classroom.name if student.classroom else None,
            "section_id": str(student.section.id) if student.section else None,
            "section_name": student.section.name if student.section else None,
            "academic_year": student.academic_year.name if student.academic_year else None,
            "admission_date": student.admission_date.isoformat() if student.admission_date else None,
            "admission_type": student.admission_type,
            "registration_type": student.registration_type,
            "admission_status": student.admission_status,
            "uses_transport": student.uses_transport,
            "transport_route": student.transport_route,
            "transport_route_name": student.transport_route_name,
            "transport_area": student.transport_area,
            "bus_stop": student.bus_stop,
            "bus_no": student.bus_no,
            "transport_fee_per_month": student.transport_fee_per_month,
            "transport_months": student.transport_months or [],
            "migration": student.migration,
            "lateral_entry": student.lateral_entry,
            "in_hostel": student.in_hostel,
            "extra_activities": student.extra_activities,
            "remarks": student.remarks,
            "referral_type": student.referral_type,
            "referral_number": student.referral_number,
            "referral_email": student.referral_email,
            "parent_info": {
                "father_name": student.parent_info.father_name if student.parent_info else None,
                "father_phone": student.parent_info.father_phone if student.parent_info else None,
                "father_email": student.parent_info.father_email if student.parent_info else None,
                "father_occupation": student.parent_info.father_occupation if student.parent_info else None,
                "mother_name": student.parent_info.mother_name if student.parent_info else None,
                "mother_phone": student.parent_info.mother_phone if student.parent_info else None,
                "guardian_name": student.parent_info.guardian_name if student.parent_info else None,
                "guardian_phone": student.parent_info.guardian_phone if student.parent_info else None,
            } if student.parent_info else None,
            "medical_info": {
                "blood_group": student.medical_info.blood_group if student.medical_info else None,
                "height": student.medical_info.height if student.medical_info else None,
                "weight": student.medical_info.weight if student.medical_info else None,
                "allergies": student.medical_info.allergies if student.medical_info else [],
                "medical_conditions": student.medical_info.medical_conditions if student.medical_info else [],
            } if student.medical_info else None,
            "documents": [
                {
                    "doc_type": d.doc_type, "doc_number": d.doc_number,
                    "file_path": d.file_path, "is_verified": d.is_verified
                } for d in (student.documents or [])
            ],
            "created_at": student.created_at.isoformat() if student.created_at else None
        }
        return success_response(data)
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")


@router.get("/{student_id}/profile-summary")
async def get_student_profile_summary(student_id: str, current_user: User = Depends(get_current_user)):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")

    attendance_query = StudentAttendance.objects(
        school=student.school,
        classroom=student.classroom,
        section=student.section
    ).order_by('-date')
    total_days = 0
    present_days = 0
    absent_days = 0
    late_days = 0
    recent_attendance = []

    for att in attendance_query:
        for rec in att.records:
            if rec.student and str(rec.student.id) == str(student.id):
                total_days += 1
                if rec.status == "Present":
                    present_days += 1
                elif rec.status == "Absent":
                    absent_days += 1
                elif rec.status == "Late":
                    late_days += 1
                    present_days += 1

                if len(recent_attendance) < 10:
                    recent_attendance.append({
                        "date": att.date.isoformat() if att.date else None,
                        "status": rec.status,
                        "remarks": rec.remarks
                    })
                break

    attendance_percentage = round((present_days / total_days * 100), 2) if total_days else 0

    invoices = list(FeeInvoice.objects(student=student).order_by('-invoice_date')[:10])
    payments = list(PaymentTransaction.objects(student=student, status="Success").order_by('-payment_date')[:10])
    fee_summary = {
        "total_invoices": FeeInvoice.objects(student=student).count(),
        "total_billed": sum(inv.net_amount or 0 for inv in FeeInvoice.objects(student=student)),
        "total_paid": sum(inv.paid_amount or 0 for inv in FeeInvoice.objects(student=student)),
        "total_due": sum(inv.balance_amount or 0 for inv in FeeInvoice.objects(student=student)),
        "recent_invoices": [{
            "id": str(inv.id),
            "invoice_no": inv.invoice_no,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "net_amount": inv.net_amount,
            "paid_amount": inv.paid_amount,
            "balance_amount": inv.balance_amount,
            "status": inv.status
        } for inv in invoices],
        "recent_payments": [{
            "id": str(payment.id),
            "transaction_no": payment.transaction_no,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "amount": payment.amount,
            "payment_mode": payment.payment_mode,
            "receipt_no": payment.receipt_no,
            "remarks": payment.remarks
        } for payment in payments]
    }

    results = list(Result.objects(student=student).order_by('-generated_at')[:10])
    result_summary = [{
        "id": str(result.id),
        "exam_name": result.exam.name if result.exam else None,
        "exam_type": result.exam.exam_type if result.exam else None,
        "generated_at": result.generated_at.isoformat() if result.generated_at else None,
        "total_obtained": result.total_obtained_marks,
        "total_max": result.total_max_marks,
        "percentage": result.percentage,
        "grade": result.overall_grade,
        "cgpa": result.cgpa,
        "rank_in_class": result.rank_in_class,
        "rank_in_section": result.rank_in_section,
        "result_status": result.result_status,
        "is_pass": result.is_pass,
        "subjects": [{
            "name": subject.subject_name,
            "obtained": subject.total_marks,
            "max": subject.max_marks,
            "grade": subject.grade,
            "is_pass": subject.is_pass
        } for subject in (result.subject_results or [])]
    } for result in results]

    tcs = list(TransferCertificate.objects(student=student).order_by('-issue_date')[:5])

    student_data = {
        "id": str(student.id),
        "admission_no": student.admission_no,
        "student_id": student.student_id,
        "full_name": student.full_name,
        "first_name": student.first_name,
        "middle_name": student.middle_name,
        "last_name": student.last_name,
        "gender": student.gender,
        "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
        "religion": student.religion,
        "caste": student.caste,
        "nationality": student.nationality,
        "aadhar_number": student.aadhar_number,
        "phone": student.phone,
        "email": student.email,
        "current_address": student.current_address,
        "permanent_address": student.permanent_address,
        "current_address_details": student.current_address_details or {},
        "permanent_address_details": student.permanent_address_details or {},
        "photo": student.photo,
        "branch_code": student.branch_code,
        "branch_name": student.branch_name,
        "classroom_name": student.classroom.name if student.classroom else None,
        "section_name": student.section.name if student.section else None,
        "academic_year": student.academic_year.name if student.academic_year else None,
        "admission_date": student.admission_date.isoformat() if student.admission_date else None,
        "admission_type": student.admission_type,
        "registration_type": student.registration_type,
        "admission_status": student.admission_status,
        "uses_transport": student.uses_transport,
        "transport_route_name": student.transport_route_name,
        "transport_area": student.transport_area,
        "bus_stop": student.bus_stop,
        "bus_no": student.bus_no,
        "transport_fee_per_month": student.transport_fee_per_month,
        "transport_months": student.transport_months or [],
        "migration": student.migration,
        "lateral_entry": student.lateral_entry,
        "in_hostel": student.in_hostel,
        "extra_activities": student.extra_activities or [],
        "remarks": student.remarks,
        "referral_type": student.referral_type,
        "referral_number": student.referral_number,
        "referral_email": student.referral_email,
        "parent_info": {
            "father_name": student.parent_info.father_name if student.parent_info else None,
            "father_phone": student.parent_info.father_phone if student.parent_info else None,
            "father_email": student.parent_info.father_email if student.parent_info else None,
            "father_occupation": student.parent_info.father_occupation if student.parent_info else None,
            "mother_name": student.parent_info.mother_name if student.parent_info else None,
            "mother_phone": student.parent_info.mother_phone if student.parent_info else None,
            "mother_email": student.parent_info.mother_email if student.parent_info else None,
            "mother_occupation": student.parent_info.mother_occupation if student.parent_info else None,
            "guardian_name": student.parent_info.guardian_name if student.parent_info else None,
            "guardian_phone": student.parent_info.guardian_phone if student.parent_info else None,
            "guardian_relation": student.parent_info.guardian_relation if student.parent_info else None,
            "guardian_address": student.parent_info.guardian_address if student.parent_info else None,
        } if student.parent_info else None,
        "medical_info": {
            "blood_group": student.medical_info.blood_group if student.medical_info else None,
            "height": student.medical_info.height if student.medical_info else None,
            "weight": student.medical_info.weight if student.medical_info else None,
            "allergies": student.medical_info.allergies if student.medical_info else [],
            "medical_conditions": student.medical_info.medical_conditions if student.medical_info else [],
            "emergency_contact": student.medical_info.emergency_contact if student.medical_info else None,
            "doctor_name": student.medical_info.doctor_name if student.medical_info else None,
            "doctor_phone": student.medical_info.doctor_phone if student.medical_info else None,
        } if student.medical_info else None,
        "documents": [
            {
                "doc_type": d.doc_type,
                "doc_number": d.doc_number,
                "file_path": d.file_path,
                "is_verified": d.is_verified,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
            } for d in (student.documents or [])
        ],
        "created_at": student.created_at.isoformat() if student.created_at else None
    }

    return success_response({
        "student": student_data,
        "attendance_summary": {
            "total_working_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "late_days": late_days,
            "attendance_percentage": attendance_percentage,
            "recent_records": recent_attendance
        },
        "fee_summary": fee_summary,
        "results": result_summary,
        "transfer_certificates": [{
            "id": str(tc.id),
            "tc_number": tc.tc_number,
            "issue_date": tc.issue_date.isoformat() if tc.issue_date else None
        } for tc in tcs]
    })


@router.put("/{student_id}")
async def update_student(student_id: str, data: dict, current_user: User = Depends(get_current_user)):
    try:
        student = Student.objects.get(id=student_id)
        
        # Handle nested updates
        parent_info = data.pop('parent_info', None)
        medical_info = data.pop('medical_info', None)
        data.pop('id', None)
        data['updated_at'] = datetime.utcnow()
        
        # Handle reference fields
        if 'classroom_id' in data:
            try:
                classroom = ClassRoom.objects.get(id=data.pop('classroom_id'))
                data['classroom'] = classroom
            except ClassRoom.DoesNotExist:
                pass
        
        if 'section_id' in data:
            try:
                section = Section.objects.get(id=data.pop('section_id'))
                data['section'] = section
            except Section.DoesNotExist:
                pass

        route_id = data.pop('transport_route_id', None)
        if 'current_address_details' in data and 'current_address' not in data:
            data['current_address'] = _normalize_address_text(data.get('current_address_details'))
        if 'permanent_address_details' in data and 'permanent_address' not in data:
            data['permanent_address'] = _normalize_address_text(data.get('permanent_address_details'))
        
        student.update(**data)
        
        if parent_info:
            from models.student import ParentInfo
            student.reload()
            student.parent_info = ParentInfo(**parent_info)
            student.save()
        
        if medical_info:
            from models.student import MedicalInfo
            student.reload()
            student.medical_info = MedicalInfo(**medical_info)
            student.save()

        student.reload()
        if route_id is not None:
            payload = StudentAdmission(
                first_name=student.first_name,
                last_name=student.last_name,
                gender=student.gender,
                school_id=str(student.school.id),
                academic_year_id=str(student.academic_year.id),
                classroom_id=str(student.classroom.id),
                section_id=str(student.section.id),
                uses_transport=data.get('uses_transport', student.uses_transport),
                transport_area=data.get('transport_area', student.transport_area),
                bus_stop=data.get('bus_stop', student.bus_stop),
                bus_no=data.get('bus_no', student.bus_no),
                transport_months=data.get('transport_months', student.transport_months or [])
            )
            _sync_student_transport(student, route_id, payload)
        
        return success_response(message="Student updated successfully")
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")


@router.delete("/{student_id}")
async def delete_student(student_id: str, current_user: User = Depends(get_current_user)):
    try:
        student = Student.objects.get(id=student_id)
        student.update(is_active=False)
        return success_response(message="Student record deactivated")
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")


@router.post("/{student_id}/upload-photo")
async def upload_student_photo(
    student_id: str, file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        student = Student.objects.get(id=student_id)
        file_path = await save_upload_file(file, "student_photos")
        student.update(photo=file_path)
        return success_response({"photo": file_path}, "Photo uploaded successfully")
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")


@router.post("/{student_id}/upload-document")
async def upload_student_document(
    student_id: str,
    doc_type: str,
    doc_number: Optional[str] = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        student = Student.objects.get(id=student_id)
        file_path = await save_upload_file(file, "student_documents")
        from models.student import StudentDocument
        doc = StudentDocument(doc_type=doc_type, doc_number=doc_number, file_path=file_path)
        student.reload()
        student.documents.append(doc)
        student.save()
        return success_response({"file_path": file_path}, "Document uploaded successfully")
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")


# ─── Transfer Certificate ─────────────────────────────────────────────────────

class TCCreate(BaseModel):
    reason: Optional[str] = None
    conduct: str = "Good"
    last_class: Optional[str] = None
    fee_clearance: bool = False
    remarks: Optional[str] = None


@router.post("/{student_id}/transfer-certificate")
async def generate_tc(
    student_id: str, data: TCCreate,
    current_user: User = Depends(get_current_user)
):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")
    
    tc_no = generate_tc_no(student.school.code)
    tc = TransferCertificate(
        student=student, school=student.school,
        tc_number=tc_no, reason=data.reason,
        conduct=data.conduct,
        last_class=data.last_class or (student.classroom.name if student.classroom else None),
        fee_clearance=data.fee_clearance,
        issued_by=current_user.full_name,
        remarks=data.remarks
    )
    tc.save()
    student.update(admission_status="Transferred")
    
    return success_response({"tc_number": tc_no, "id": str(tc.id)}, "Transfer certificate generated")


@router.get("/{student_id}/transfer-certificate")
async def get_tc(student_id: str, current_user: User = Depends(get_current_user)):
    try:
        student = Student.objects.get(id=student_id)
        tcs = TransferCertificate.objects(student=student).order_by('-created_at')
        result = [{
            "id": str(tc.id), "tc_number": tc.tc_number,
            "issue_date": tc.issue_date.isoformat() if tc.issue_date else None,
            "conduct": tc.conduct, "reason": tc.reason,
            "fee_clearance": tc.fee_clearance, "issued_by": tc.issued_by
        } for tc in tcs]
        return success_response(result)
    except Student.DoesNotExist:
        raise HTTPException(404, "Student not found")


@router.get("/stats/summary")
async def student_stats(school_id: str, academic_year_id: Optional[str] = None,
                        branch_code: Optional[str] = None,
                        current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        query = Student.objects(school=school, is_active=True)
        if academic_year_id:
            ay = AcademicYear.objects.get(id=academic_year_id)
            query = query.filter(academic_year=ay)
        if branch_code:
            query = query.filter(branch_code=branch_code)
        
        stats = {
            "total": query.count(),
            "by_gender": {
                "male": query.filter(gender="Male").count(),
                "female": query.filter(gender="Female").count(),
                "other": query.filter(gender="Other").count()
            },
            "by_status": {
                "active": query.filter(admission_status="Active").count(),
                "transferred": query.filter(admission_status="Transferred").count(),
                "alumni": query.filter(admission_status="Alumni").count(),
            }
        }
        return success_response(stats)
    except School.DoesNotExist:
        raise HTTPException(404, "School not found")

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.student import Student, TransferCertificate
from models.institution import School, AcademicYear, ClassRoom, Section, User
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
    school_id: str
    academic_year_id: str
    classroom_id: str
    section_id: str
    admission_date: Optional[datetime] = None
    admission_type: str = "New"
    parent_info: Optional[dict] = None
    medical_info: Optional[dict] = None
    previous_school: Optional[dict] = None
    uses_transport: bool = False
    in_hostel: bool = False
    extra_activities: List[str] = []
    remarks: Optional[str] = None


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
        current_address=data.current_address,
        permanent_address=data.permanent_address,
        school=school,
        academic_year=ay,
        classroom=classroom,
        section=section,
        admission_date=data.admission_date or datetime.utcnow(),
        admission_type=data.admission_type,
        uses_transport=data.uses_transport,
        in_hostel=data.in_hostel,
        extra_activities=data.extra_activities,
        remarks=data.remarks
    )
    
    if data.parent_info:
        from models.student import ParentInfo
        student.parent_info = ParentInfo(**data.parent_info)
    
    if data.medical_info:
        from models.student import MedicalInfo
        student.medical_info = MedicalInfo(**data.medical_info)
    
    student.save()
    
    return success_response({
        "id": str(student.id),
        "admission_no": student.admission_no,
        "student_id": student.student_id,
        "full_name": student.full_name
    }, "Student admitted successfully")


@router.get("")
async def list_students(
    school_id: str,
    academic_year_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    section_id: Optional[str] = None,
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
            "admission_status": s.admission_status,
            "phone": s.phone,
            "photo": s.photo,
            "father_name": s.parent_info.father_name if s.parent_info else None,
            "father_phone": s.parent_info.father_phone if s.parent_info else None,
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
            "photo": student.photo,
            "classroom_id": str(student.classroom.id) if student.classroom else None,
            "classroom_name": student.classroom.name if student.classroom else None,
            "section_id": str(student.section.id) if student.section else None,
            "section_name": student.section.name if student.section else None,
            "academic_year": student.academic_year.name if student.academic_year else None,
            "admission_date": student.admission_date.isoformat() if student.admission_date else None,
            "admission_type": student.admission_type,
            "admission_status": student.admission_status,
            "uses_transport": student.uses_transport,
            "in_hostel": student.in_hostel,
            "extra_activities": student.extra_activities,
            "remarks": student.remarks,
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
        from models.student import Document as DocModel
        doc = DocModel(doc_type=doc_type, doc_number=doc_number, file_path=file_path)
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
                        current_user: User = Depends(get_current_user)):
    try:
        school = School.objects.get(id=school_id)
        query = Student.objects(school=school, is_active=True)
        if academic_year_id:
            ay = AcademicYear.objects.get(id=academic_year_id)
            query = query.filter(academic_year=ay)
        
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

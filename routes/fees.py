from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.fees import FeeCategory, FeeStructure, FeeInvoice, PaymentTransaction, FeeDiscount
from models.institution import School, AcademicYear, ClassRoom, User
from models.student import Student
from utils.auth import get_current_user
from utils.helpers import success_response, generate_invoice_no, generate_transaction_no

router = APIRouter(prefix="/fees", tags=["Fees Management"])


# ─── Fee Category ─────────────────────────────────────────────────────────────

@router.post("/category")
async def create_fee_category(data: dict, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data['school_id'])
    cat = FeeCategory(
        school=school, name=data['name'], code=data['code'],
        description=data.get('description'),
        is_mandatory=data.get('is_mandatory', True)
    )
    cat.save()
    return success_response({"id": str(cat.id)}, "Fee category created")


@router.get("/category")
async def list_fee_categories(school_id: str, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=school_id)
    cats = FeeCategory.objects(school=school, is_active=True)
    result = [{"id": str(c.id), "name": c.name, "code": c.code, "is_mandatory": c.is_mandatory} for c in cats]
    return success_response(result)


# ─── Fee Structure ────────────────────────────────────────────────────────────

class FeeStructureCreate(BaseModel):
    school_id: str
    academic_year_id: str
    classroom_id: str
    name: str
    items: List[dict]
    installments: int = 1
    late_fee_per_day: float = 0
    grace_days: int = 0


@router.post("/structure")
async def create_fee_structure(data: FeeStructureCreate, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data.school_id)
    ay = AcademicYear.objects.get(id=data.academic_year_id)
    classroom = ClassRoom.objects.get(id=data.classroom_id)
    
    from models.fees import FeeStructureItem
    
    fs = FeeStructure(
        school=school, academic_year=ay, classroom=classroom,
        name=data.name, installments=data.installments,
        late_fee_per_day=data.late_fee_per_day,
        grace_days=data.grace_days
    )
    
    total = 0
    for item in data.items:
        cat = FeeCategory.objects.get(id=item['category_id'])
        fi = FeeStructureItem(category=cat, category_name=cat.name, amount=item['amount'])
        fs.items.append(fi)
        total += item['amount']
    
    fs.total_amount = total
    fs.save()
    return success_response({"id": str(fs.id), "total_amount": total}, "Fee structure created")


@router.get("/structure")
async def list_fee_structures(
    school_id: str,
    academic_year_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = FeeStructure.objects(school=school, is_active=True)
    if academic_year_id:
        ay = AcademicYear.objects.get(id=academic_year_id)
        query = query.filter(academic_year=ay)
    if classroom_id:
        cls = ClassRoom.objects.get(id=classroom_id)
        query = query.filter(classroom=cls)
    
    result = [{
        "id": str(f.id),
        "name": f.name,
        "classroom": f.classroom.name if f.classroom else None,
        "total_amount": f.total_amount,
        "installments": f.installments,
        "items": [{"category": i.category_name, "amount": i.amount} for i in f.items]
    } for f in query]
    return success_response(result)


# ─── Invoice ──────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    school_id: str
    student_id: str
    academic_year_id: str
    fee_structure_id: Optional[str] = None
    items: List[dict]
    due_date: Optional[datetime] = None
    discount_amount: float = 0
    remarks: Optional[str] = None


@router.post("/invoice")
async def create_invoice(data: InvoiceCreate, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data.school_id)
    student = Student.objects.get(id=data.student_id)
    ay = AcademicYear.objects.get(id=data.academic_year_id)
    
    invoice_no = generate_invoice_no(school.code)
    gross = sum(item['amount'] for item in data.items)
    net = gross - data.discount_amount
    
    invoice = FeeInvoice(
        school=school, student=student, academic_year=ay,
        invoice_no=invoice_no,
        due_date=data.due_date,
        items=data.items,
        gross_amount=gross,
        discount_amount=data.discount_amount,
        net_amount=net,
        balance_amount=net,
        remarks=data.remarks,
        generated_by=current_user.full_name
    )
    invoice.save()
    return success_response({
        "id": str(invoice.id),
        "invoice_no": invoice_no,
        "net_amount": net
    }, "Invoice created successfully")


@router.get("/invoice")
async def list_invoices(
    school_id: str,
    student_id: Optional[str] = None,
    academic_year_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = FeeInvoice.objects(school=school)
    
    if student_id:
        student = Student.objects.get(id=student_id)
        query = query.filter(student=student)
    if academic_year_id:
        ay = AcademicYear.objects.get(id=academic_year_id)
        query = query.filter(academic_year=ay)
    if status:
        query = query.filter(status=status)
    
    total = query.count()
    invoices = query.order_by('-created_at').skip((page - 1) * per_page).limit(per_page)
    
    result = [{
        "id": str(inv.id),
        "invoice_no": inv.invoice_no,
        "student_name": inv.student.full_name if inv.student else None,
        "student_id": str(inv.student.id) if inv.student else None,
        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "gross_amount": inv.gross_amount,
        "discount_amount": inv.discount_amount,
        "net_amount": inv.net_amount,
        "paid_amount": inv.paid_amount,
        "balance_amount": inv.balance_amount,
        "status": inv.status
    } for inv in invoices]
    
    return success_response(result, meta={
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    })


@router.get("/invoice/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: User = Depends(get_current_user)):
    try:
        inv = FeeInvoice.objects.get(id=invoice_id)
        # Get transactions
        transactions = PaymentTransaction.objects(invoice=inv).order_by('-payment_date')
        
        data = {
            "id": str(inv.id),
            "invoice_no": inv.invoice_no,
            "student_name": inv.student.full_name if inv.student else None,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "items": inv.items,
            "gross_amount": inv.gross_amount,
            "discount_amount": inv.discount_amount,
            "late_fee": inv.late_fee,
            "net_amount": inv.net_amount,
            "paid_amount": inv.paid_amount,
            "balance_amount": inv.balance_amount,
            "status": inv.status,
            "remarks": inv.remarks,
            "transactions": [{
                "id": str(t.id),
                "transaction_no": t.transaction_no,
                "amount": t.amount,
                "payment_date": t.payment_date.isoformat() if t.payment_date else None,
                "payment_mode": t.payment_mode,
                "status": t.status
            } for t in transactions]
        }
        return success_response(data)
    except FeeInvoice.DoesNotExist:
        raise HTTPException(404, "Invoice not found")


# ─── Payment ──────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    school_id: str
    student_id: str
    invoice_id: str
    amount: float
    payment_mode: str
    payment_date: Optional[datetime] = None
    instrument_no: Optional[str] = None
    bank_name: Optional[str] = None
    remarks: Optional[str] = None


@router.post("/payment")
async def record_payment(data: PaymentCreate, current_user: User = Depends(get_current_user)):
    school = School.objects.get(id=data.school_id)
    student = Student.objects.get(id=data.student_id)
    invoice = FeeInvoice.objects.get(id=data.invoice_id)
    
    if data.amount <= 0:
        raise HTTPException(400, "Payment amount must be positive")
    if data.amount > invoice.balance_amount:
        raise HTTPException(400, f"Payment amount exceeds balance: {invoice.balance_amount}")
    
    txn_no = generate_transaction_no()
    
    txn = PaymentTransaction(
        school=school, student=student, invoice=invoice,
        transaction_no=txn_no,
        payment_date=data.payment_date or datetime.utcnow(),
        amount=data.amount,
        payment_mode=data.payment_mode,
        instrument_no=data.instrument_no,
        bank_name=data.bank_name,
        remarks=data.remarks,
        collected_by=current_user.full_name,
        receipt_no=f"RCP-{txn_no[-8:]}"
    )
    txn.save()
    
    # Update invoice
    new_paid = invoice.paid_amount + data.amount
    new_balance = invoice.net_amount + invoice.late_fee - new_paid
    
    if new_balance <= 0:
        new_status = "Paid"
    elif new_paid > 0:
        new_status = "Partial"
    else:
        new_status = "Pending"
    
    invoice.update(
        paid_amount=new_paid,
        balance_amount=max(0, new_balance),
        status=new_status
    )
    
    return success_response({
        "transaction_no": txn_no,
        "receipt_no": txn.receipt_no,
        "amount": data.amount,
        "balance": max(0, new_balance),
        "status": new_status
    }, "Payment recorded successfully")


@router.get("/dues")
async def get_fee_dues(
    school_id: str,
    academic_year_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = FeeInvoice.objects(school=school, status__in=["Pending", "Partial", "Overdue"])
    
    if academic_year_id:
        ay = AcademicYear.objects.get(id=academic_year_id)
        query = query.filter(academic_year=ay)
    
    total_due = sum(inv.balance_amount for inv in query)
    count = query.count()
    
    return success_response({
        "total_pending_invoices": count,
        "total_due_amount": total_due,
        "invoices": [{
            "invoice_no": inv.invoice_no,
            "student_name": inv.student.full_name if inv.student else None,
            "net_amount": inv.net_amount,
            "paid_amount": inv.paid_amount,
            "balance": inv.balance_amount,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv.status
        } for inv in query.order_by('due_date')[:50]]
    })


@router.get("/reports/summary")
async def fee_summary(
    school_id: str,
    academic_year_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    school = School.objects.get(id=school_id)
    query = FeeInvoice.objects(school=school)
    
    if academic_year_id:
        ay = AcademicYear.objects.get(id=academic_year_id)
        query = query.filter(academic_year=ay)
    
    total_billed = sum(inv.net_amount for inv in query)
    total_collected = sum(inv.paid_amount for inv in query)
    total_due = total_billed - total_collected
    
    return success_response({
        "total_billed": total_billed,
        "total_collected": total_collected,
        "total_due": total_due,
        "collection_rate": round((total_collected / total_billed * 100) if total_billed > 0 else 0, 2),
        "by_status": {
            "paid": query.filter(status="Paid").count(),
            "partial": query.filter(status="Partial").count(),
            "pending": query.filter(status="Pending").count(),
            "overdue": query.filter(status="Overdue").count()
        }
    })

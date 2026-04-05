from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.models import (
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
from app.schemas import (
    ContactInquiryCreate,
    ContactInquiryOut,
    ContactInfoOut,
    HeroContentOut,
    HomePageOut,
    NewsletterCreate,
    NewsletterOut,
    PortfolioCaseOut,
    ProcessStepOut,
    ProductOut,
    ReasonOut,
    SectionContentOut,
    ServiceOut,
    SocialLinkOut,
    StatOut,
    TestimonialOut,
)
from app.serializers import document_to_dict, documents_to_dict


router = APIRouter(prefix="/api/v1", tags=["Public API"])


def ordered(model):
    return list(model.objects.order_by("sort_order", "id"))


@router.get("/home", response_model=HomePageOut)
def get_homepage(_: None = Depends(get_db)):
    hero = HeroContent.objects.first()
    contact = ContactInfo.objects.first()
    if not hero or not contact:
        raise HTTPException(status_code=500, detail="Seed data is missing")
    return HomePageOut(
        hero=HeroContentOut.model_validate(document_to_dict(hero)),
        contact=ContactInfoOut.model_validate(document_to_dict(contact)),
        sections=[SectionContentOut.model_validate(item) for item in documents_to_dict(SectionContent.objects.order_by("section_key"))],
        services=[ServiceOut.model_validate(item) for item in documents_to_dict(ordered(Service))],
        stats=[StatOut.model_validate(item) for item in documents_to_dict(ordered(Stat))],
        products=[ProductOut.model_validate(item) for item in documents_to_dict(ordered(Product))],
        process_steps=[ProcessStepOut.model_validate(item) for item in documents_to_dict(ordered(ProcessStep))],
        portfolio_cases=[PortfolioCaseOut.model_validate(item) for item in documents_to_dict(ordered(PortfolioCase))],
        testimonials=[TestimonialOut.model_validate(item) for item in documents_to_dict(ordered(Testimonial))],
        reasons=[ReasonOut.model_validate(item) for item in documents_to_dict(ordered(Reason))],
        social_links=[SocialLinkOut.model_validate(item) for item in documents_to_dict(ordered(SocialLink))],
    )


@router.get("/hero", response_model=HeroContentOut)
def get_hero(_: None = Depends(get_db)):
    return HeroContentOut.model_validate(document_to_dict(HeroContent.objects.first()))


@router.get("/contact-info", response_model=ContactInfoOut)
def get_contact_info(_: None = Depends(get_db)):
    return ContactInfoOut.model_validate(document_to_dict(ContactInfo.objects.first()))


@router.get("/sections", response_model=list[SectionContentOut])
def get_sections(_: None = Depends(get_db)):
    return [SectionContentOut.model_validate(item) for item in documents_to_dict(SectionContent.objects.order_by("section_key"))]


@router.get("/services", response_model=list[ServiceOut])
def get_services(_: None = Depends(get_db)):
    return [ServiceOut.model_validate(item) for item in documents_to_dict(ordered(Service))]


@router.get("/stats", response_model=list[StatOut])
def get_stats(_: None = Depends(get_db)):
    return [StatOut.model_validate(item) for item in documents_to_dict(ordered(Stat))]


@router.get("/products", response_model=list[ProductOut])
def get_products(_: None = Depends(get_db)):
    return [ProductOut.model_validate(item) for item in documents_to_dict(ordered(Product))]


@router.get("/process-steps", response_model=list[ProcessStepOut])
def get_process_steps(_: None = Depends(get_db)):
    return [ProcessStepOut.model_validate(item) for item in documents_to_dict(ordered(ProcessStep))]


@router.get("/portfolio-cases", response_model=list[PortfolioCaseOut])
def get_portfolio_cases(_: None = Depends(get_db)):
    return [PortfolioCaseOut.model_validate(item) for item in documents_to_dict(ordered(PortfolioCase))]


@router.get("/testimonials", response_model=list[TestimonialOut])
def get_testimonials(_: None = Depends(get_db)):
    return [TestimonialOut.model_validate(item) for item in documents_to_dict(ordered(Testimonial))]


@router.get("/reasons", response_model=list[ReasonOut])
def get_reasons(_: None = Depends(get_db)):
    return [ReasonOut.model_validate(item) for item in documents_to_dict(ordered(Reason))]


@router.get("/social-links", response_model=list[SocialLinkOut])
def get_social_links(_: None = Depends(get_db)):
    return [SocialLinkOut.model_validate(item) for item in documents_to_dict(ordered(SocialLink))]


@router.post("/contact-inquiries", response_model=ContactInquiryOut, status_code=status.HTTP_201_CREATED)
def create_contact_inquiry(payload: ContactInquiryCreate, _: None = Depends(get_db)):
    inquiry = ContactInquiry(**payload.model_dump()).save()
    return ContactInquiryOut.model_validate(document_to_dict(inquiry))


@router.post("/newsletter-subscriptions", response_model=NewsletterOut, status_code=status.HTTP_201_CREATED)
def create_newsletter_subscription(payload: NewsletterCreate, _: None = Depends(get_db)):
    existing = NewsletterSubscription.objects(email=payload.email).first()
    if existing:
        return NewsletterOut.model_validate(document_to_dict(existing))
    subscription = NewsletterSubscription(email=payload.email).save()
    return NewsletterOut.model_validate(document_to_dict(subscription))

from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field


class ORMBase(BaseModel):
    model_config = {"from_attributes": True}


class HeroContentOut(ORMBase):
    availability_badge: str
    title_prefix: str
    title_highlight: str
    rotating_words: List[str]
    subheading: str
    tech_tags: List[str]
    bottom_text: str
    primary_cta_text: str


class ContactInfoOut(ORMBase):
    email: str
    phone_numbers: List[str]
    location: str
    heading: str
    subheading: str
    form_title: str


class SectionContentOut(ORMBase):
    section_key: str
    kicker: str
    title: str
    highlight: str
    description: str


class ServiceOut(ORMBase):
    id: str
    sort_order: int
    number: str
    title: str
    description: str
    icon_name: str
    is_active: bool


class StatOut(ORMBase):
    id: str
    sort_order: int
    value: float
    suffix: str
    label: str
    sub_label: str


class ProductOut(ORMBase):
    id: str
    sort_order: int
    code: str
    badge: str
    title: str
    subtitle: str
    description: str
    tags: List[str]
    gradient_class: str
    accent_class: str


class ProcessStepOut(ORMBase):
    id: str
    sort_order: int
    phase: str
    title: str
    description: str
    details: List[str]
    icon_name: str


class PortfolioCaseOut(ORMBase):
    id: str
    sort_order: int
    code: str
    title: str
    category: str
    image_path: str


class TestimonialOut(ORMBase):
    id: str
    sort_order: int
    name: str
    role: str
    rating: int
    quote: str


class ReasonOut(ORMBase):
    id: str
    sort_order: int
    title: str
    description: str
    icon_name: str


class SocialLinkOut(ORMBase):
    id: str
    sort_order: int
    label: str
    href: str
    icon_name: str


class ContactInquiryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    project_type: str = Field(..., min_length=2, max_length=180)
    budget_range: str = Field(default="", max_length=80)
    message: str = Field(..., min_length=10, max_length=4000)


class ContactInquiryOut(ORMBase):
    id: str
    name: str
    email: EmailStr
    project_type: str
    budget_range: str
    message: str
    status: str
    created_at: datetime


class NewsletterCreate(BaseModel):
    email: EmailStr


class NewsletterOut(ORMBase):
    id: str
    email: EmailStr
    status: str
    created_at: datetime


class HomePageOut(BaseModel):
    hero: HeroContentOut
    contact: ContactInfoOut
    sections: List[SectionContentOut]
    services: List[ServiceOut]
    stats: List[StatOut]
    products: List[ProductOut]
    process_steps: List[ProcessStepOut]
    portfolio_cases: List[PortfolioCaseOut]
    testimonials: List[TestimonialOut]
    reasons: List[ReasonOut]
    social_links: List[SocialLinkOut]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

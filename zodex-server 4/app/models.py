from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmailField,
    FloatField,
    IntField,
    ListField,
    StringField,
)


class TimestampedDocument(Document):
    meta = {"abstract": True}

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        if not self.created_at:
            self.created_at = datetime.utcnow()
        return super().save(*args, **kwargs)


class AdminUser(TimestampedDocument):
    username = StringField(required=True, unique=True)
    full_name = StringField(required=True)
    password_hash = StringField(required=True)
    is_active = BooleanField(default=True)

    meta = {"collection": "admin_users"}


class HeroContent(TimestampedDocument):
    availability_badge = StringField(required=True)
    title_prefix = StringField(required=True)
    title_highlight = StringField(required=True)
    rotating_words = ListField(StringField(), default=list)
    subheading = StringField(required=True)
    tech_tags = ListField(StringField(), default=list)
    bottom_text = StringField(required=True)
    primary_cta_text = StringField(required=True)

    meta = {"collection": "hero_content"}


class ContactInfo(TimestampedDocument):
    email = EmailField(required=True)
    phone_numbers = ListField(StringField(), default=list)
    location = StringField(required=True)
    heading = StringField(required=True)
    subheading = StringField(required=True)
    form_title = StringField(required=True)

    meta = {"collection": "contact_info"}


class SectionContent(TimestampedDocument):
    section_key = StringField(required=True, unique=True)
    kicker = StringField(required=True)
    title = StringField(required=True)
    highlight = StringField(required=True)
    description = StringField(required=True)

    meta = {"collection": "section_content"}


class Service(TimestampedDocument):
    sort_order = IntField(default=0)
    number = StringField(required=True)
    title = StringField(required=True)
    description = StringField(required=True)
    icon_name = StringField(default="box")
    is_active = BooleanField(default=True)

    meta = {"collection": "services", "ordering": ["sort_order", "id"]}


class Stat(TimestampedDocument):
    sort_order = IntField(default=0)
    value = FloatField(required=True)
    suffix = StringField(default="")
    label = StringField(required=True)
    sub_label = StringField(required=True)

    meta = {"collection": "stats", "ordering": ["sort_order", "id"]}


class Product(TimestampedDocument):
    sort_order = IntField(default=0)
    code = StringField(required=True)
    badge = StringField(required=True)
    title = StringField(required=True)
    subtitle = StringField(required=True)
    description = StringField(required=True)
    tags = ListField(StringField(), default=list)
    gradient_class = StringField(default="")
    accent_class = StringField(default="")

    meta = {"collection": "products", "ordering": ["sort_order", "id"]}


class ProcessStep(TimestampedDocument):
    sort_order = IntField(default=0)
    phase = StringField(required=True)
    title = StringField(required=True)
    description = StringField(required=True)
    details = ListField(StringField(), default=list)
    icon_name = StringField(default="circle")

    meta = {"collection": "process_steps", "ordering": ["sort_order", "id"]}


class PortfolioCase(TimestampedDocument):
    sort_order = IntField(default=0)
    code = StringField(required=True)
    title = StringField(required=True)
    category = StringField(required=True)
    image_path = StringField(required=True)

    meta = {"collection": "portfolio_cases", "ordering": ["sort_order", "id"]}


class Testimonial(TimestampedDocument):
    sort_order = IntField(default=0)
    name = StringField(required=True)
    role = StringField(required=True)
    rating = IntField(default=5)
    quote = StringField(required=True)

    meta = {"collection": "testimonials", "ordering": ["sort_order", "id"]}


class Reason(TimestampedDocument):
    sort_order = IntField(default=0)
    title = StringField(required=True)
    description = StringField(required=True)
    icon_name = StringField(default="sparkles")

    meta = {"collection": "reasons", "ordering": ["sort_order", "id"]}


class SocialLink(TimestampedDocument):
    sort_order = IntField(default=0)
    label = StringField(required=True)
    href = StringField(required=True)
    icon_name = StringField(default="link")

    meta = {"collection": "social_links", "ordering": ["sort_order", "id"]}


class ContactInquiry(TimestampedDocument):
    name = StringField(required=True)
    email = EmailField(required=True)
    project_type = StringField(required=True)
    budget_range = StringField(default="")
    message = StringField(required=True)
    status = StringField(default="new")

    meta = {"collection": "contact_inquiries"}


class NewsletterSubscription(TimestampedDocument):
    email = EmailField(required=True, unique=True)
    status = StringField(default="subscribed")

    meta = {"collection": "newsletter_subscriptions"}

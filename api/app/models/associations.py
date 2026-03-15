"""Many-to-Many association link tables for all content entities."""
import uuid
from sqlmodel import SQLModel, Field


class ProductApplicationLink(SQLModel, table=True):
    __tablename__ = "product_application_links"
    product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)
    application_id: uuid.UUID = Field(foreign_key="applications.id", primary_key=True)


class ProductCertificationLink(SQLModel, table=True):
    __tablename__ = "product_certification_links"
    product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)
    certification_id: uuid.UUID = Field(foreign_key="certifications.id", primary_key=True)


class ProductFAQLink(SQLModel, table=True):
    __tablename__ = "product_faq_links"
    product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)
    faq_item_id: uuid.UUID = Field(foreign_key="faq_items.id", primary_key=True)
    sort_order: int = Field(default=0)


class ProductComparisonLink(SQLModel, table=True):
    __tablename__ = "product_comparison_links"
    product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)
    comparison_topic_id: uuid.UUID = Field(foreign_key="comparison_topics.id", primary_key=True)


class AlternativePartLink(SQLModel, table=True):
    """Self-referential M2M for alternative / substitute products."""
    __tablename__ = "alternative_part_links"
    product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)
    alternative_product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)
    relation: str = Field(default="substitute", max_length=30)  # "substitute" | "upgrade"
    note: str = Field(default="", max_length=200)


class ApplicationFAQLink(SQLModel, table=True):
    __tablename__ = "application_faq_links"
    application_id: uuid.UUID = Field(foreign_key="applications.id", primary_key=True)
    faq_item_id: uuid.UUID = Field(foreign_key="faq_items.id", primary_key=True)
    sort_order: int = Field(default=0)


class ApplicationRelatedLink(SQLModel, table=True):
    """Self-referential M2M for related applications."""
    __tablename__ = "application_related_links"
    application_id: uuid.UUID = Field(foreign_key="applications.id", primary_key=True)
    related_application_id: uuid.UUID = Field(foreign_key="applications.id", primary_key=True)

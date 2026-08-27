"""initial_schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === users ===
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=30), nullable=False, server_default='sales'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # === product_categories ===
    op.create_table(
        'product_categories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('category_name', sa.String(length=60), nullable=False),
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('parent_id', sa.Uuid(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('seo_title', sa.String(length=70), nullable=True),
        sa.Column('seo_description', sa.String(length=160), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['product_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_product_categories_slug', 'product_categories', ['slug'], unique=True)

    # === products ===
    op.create_table(
        'products',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('model_number', sa.String(length=50), nullable=False),
        sa.Column('short_description', sa.String(length=200), nullable=False),
        sa.Column('full_description', sa.Text(), nullable=True),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('seo_title', sa.String(length=70), nullable=True),
        sa.Column('seo_description', sa.String(length=160), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['product_categories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_products_slug', 'products', ['slug'], unique=True)
    op.create_index('ix_products_model_number', 'products', ['model_number'], unique=True)
    op.create_index('ix_products_product_name', 'products', ['product_name'])

    # === applications ===
    op.create_table(
        'applications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('industry', sa.String(length=60), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('challenge', sa.Text(), nullable=True),
        sa.Column('solution', sa.Text(), nullable=True),
        sa.Column('hero_image_url', sa.String(length=500), nullable=True),
        sa.Column('seo_title', sa.String(length=70), nullable=True),
        sa.Column('seo_description', sa.String(length=160), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_applications_slug', 'applications', ['slug'], unique=True)
    op.create_index('ix_applications_application_name', 'applications', ['application_name'])

    # === faq_items ===
    op.create_table(
        'faq_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('question', sa.String(length=300), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category_tag', sa.String(length=60), nullable=True),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # === comparison_topics ===
    op.create_table(
        'comparison_topics',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('topic_title', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=True),
        sa.Column('dimensions', sa.Text(), nullable=True),
        sa.Column('conclusion', sa.Text(), nullable=True),
        sa.Column('seo_title', sa.String(length=70), nullable=True),
        sa.Column('seo_description', sa.String(length=160), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_comparison_topics_slug', 'comparison_topics', ['slug'], unique=True)
    op.create_index('ix_comparison_topics_topic_title', 'comparison_topics', ['topic_title'])

    # === certifications ===
    op.create_table(
        'certifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cert_name', sa.String(length=100), nullable=False),
        sa.Column('issuer', sa.String(length=120), nullable=True),
        sa.Column('cert_number', sa.String(length=80), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('badge_image_url', sa.String(length=500), nullable=True),
        sa.Column('document_url', sa.String(length=500), nullable=True),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_certifications_cert_name', 'certifications', ['cert_name'])

    # === capabilities ===
    op.create_table(
        'capabilities',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('capability_name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('icon_url', sa.String(length=500), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('short_description', sa.String(length=200), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),
        sa.Column('category_tag', sa.String(length=60), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_capabilities_slug', 'capabilities', ['slug'], unique=True)

    # === ctas ===
    op.create_table(
        'ctas',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cta_key', sa.String(length=60), nullable=False),
        sa.Column('cta_type', sa.String(length=30), nullable=False),
        sa.Column('headline', sa.String(length=120), nullable=False),
        sa.Column('subheadline', sa.String(length=240), nullable=True),
        sa.Column('button_label', sa.String(length=60), nullable=False),
        sa.Column('button_action', sa.String(length=30), nullable=False),
        sa.Column('button_url', sa.String(length=500), nullable=True),
        sa.Column('bg_color', sa.String(length=20), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ctas_cta_key', 'ctas', ['cta_key'], unique=True)

    # === pages ===
    op.create_table(
        'pages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('page_type', sa.String(length=40), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('subtitle', sa.String(length=240), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('hero_image_url', sa.String(length=500), nullable=True),
        sa.Column('seo_title', sa.String(length=70), nullable=True),
        sa.Column('seo_description', sa.String(length=160), nullable=True),
        sa.Column('og_image_url', sa.String(length=500), nullable=True),
        sa.Column('canonical_url', sa.String(length=500), nullable=True),
        sa.Column('structured_data', sa.Text(), nullable=True),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pages_slug', 'pages', ['slug'], unique=True)
    op.create_index('ix_pages_page_type', 'pages', ['page_type'])

    # === page_briefs ===
    op.create_table(
        'page_briefs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('target_page_type', sa.String(length=40), nullable=False),
        sa.Column('target_slug', sa.String(length=120), nullable=True),
        sa.Column('title_draft', sa.String(length=120), nullable=True),
        sa.Column('audience_persona', sa.String(length=200), nullable=True),
        sa.Column('buyer_stage', sa.String(length=40), nullable=True),
        sa.Column('primary_keyword', sa.String(length=100), nullable=True),
        sa.Column('secondary_keywords', sa.Text(), nullable=True),
        sa.Column('tone', sa.String(length=40), nullable=True),
        sa.Column('word_count_target', sa.Integer(), nullable=True),
        sa.Column('main_cta_key', sa.String(length=60), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('ai_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default='en'),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # === content_assets ===
    op.create_table(
        'content_assets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('r2_key', sa.String(length=500), nullable=False),
        sa.Column('public_url', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=80), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('asset_type', sa.String(length=30), nullable=False),
        sa.Column('alt_text', sa.String(length=200), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('product_id', sa.Uuid(), nullable=True),
        sa.Column('page_id', sa.Uuid(), nullable=True),
        sa.Column('uploaded_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_assets_r2_key', 'content_assets', ['r2_key'], unique=True)

    # === M2M link tables ===
    op.create_table(
        'product_application_links',
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'application_id'),
    )

    op.create_table(
        'product_certification_links',
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('certification_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['certification_id'], ['certifications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'certification_id'),
    )

    op.create_table(
        'product_faq_links',
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('faq_item_id', sa.Uuid(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['faq_item_id'], ['faq_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'faq_item_id'),
    )

    op.create_table(
        'product_comparison_links',
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('comparison_topic_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['comparison_topic_id'], ['comparison_topics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'comparison_topic_id'),
    )

    op.create_table(
        'alternative_part_links',
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('alternative_product_id', sa.Uuid(), nullable=False),
        sa.Column('relation', sa.String(length=30), nullable=False, server_default='substitute'),
        sa.Column('note', sa.String(length=200), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['alternative_product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'alternative_product_id'),
    )

    op.create_table(
        'application_faq_links',
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('faq_item_id', sa.Uuid(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['faq_item_id'], ['faq_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('application_id', 'faq_item_id'),
    )

    op.create_table(
        'application_related_links',
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('related_application_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('application_id', 'related_application_id'),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table('application_related_links')
    op.drop_table('application_faq_links')
    op.drop_table('alternative_part_links')
    op.drop_table('product_comparison_links')
    op.drop_table('product_faq_links')
    op.drop_table('product_certification_links')
    op.drop_table('product_application_links')
    op.drop_index('ix_content_assets_r2_key', table_name='content_assets')
    op.drop_table('content_assets')
    op.drop_table('page_briefs')
    op.drop_index('ix_pages_slug', table_name='pages')
    op.drop_index('ix_pages_page_type', table_name='pages')
    op.drop_table('pages')
    op.drop_index('ix_ctas_cta_key', table_name='ctas')
    op.drop_table('ctas')
    op.drop_index('ix_capabilities_slug', table_name='capabilities')
    op.drop_table('capabilities')
    op.drop_index('ix_certifications_cert_name', table_name='certifications')
    op.drop_table('certifications')
    op.drop_index('ix_comparison_topics_slug', table_name='comparison_topics')
    op.drop_index('ix_comparison_topics_topic_title', table_name='comparison_topics')
    op.drop_table('comparison_topics')
    op.drop_table('faq_items')
    op.drop_index('ix_applications_slug', table_name='applications')
    op.drop_index('ix_applications_application_name', table_name='applications')
    op.drop_table('applications')
    op.drop_index('ix_products_slug', table_name='products')
    op.drop_index('ix_products_model_number', table_name='products')
    op.drop_index('ix_products_product_name', table_name='products')
    op.drop_table('products')
    op.drop_index('ix_product_categories_slug', table_name='product_categories')
    op.drop_table('product_categories')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

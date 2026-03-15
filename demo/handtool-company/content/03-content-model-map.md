# ForgeBase Model Mapping

This file maps the demo-company content plan to ForgeBase's current content entities so that future seed generation stays aligned with the live system.

## 1. Product Categories

ForgeBase model: `ProductCategory`

Required/important fields:
- `category_name`
- `slug`
- `description`
- `image_url`
- `sort_order`
- `seo_title`
- `seo_description`
- `status`
- `locale`

Planned use:
- 5 main categories
- optional future second-level subcategories if needed

## 2. Products

ForgeBase model: `Product`

Required/important fields:
- `product_name`
- `slug`
- `model_number`
- `short_description`
- `full_description`
- `specifications`
- `category_id`
- `seo_title`
- `seo_description`
- `status`
- `locale`

Planned use:
- 24 to 36 products in the first believable demo set
- each product should map to at least one application where possible
- selected products should connect to gated downloadable assets

## 3. Applications

ForgeBase model: `Application`

Required/important fields:
- `application_name`
- `slug`
- `industry`
- `description`
- `challenge`
- `solution`
- `hero_image_url`
- `seo_title`
- `seo_description`
- `status`
- `locale`
- `sort_order`

Planned use:
- 6 to 8 applications
- every application should link to multiple products

## 4. Certifications

ForgeBase model: `Certification`

Required/important fields:
- `cert_name`
- `slug`
- `issuer`
- `cert_number`
- `issued_at`
- `expires_at`
- `description`
- `badge_image_url`
- `document_url`
- `locale`
- `status`

Planned use:
- 4 to 6 compliance/certification items
- selected certifications linked to relevant products

## 5. Capabilities

ForgeBase model: `Capability`

Planned capability pages:
- OEM and custom development
- private-label packaging
- quality inspection workflow
- torque verification and calibration
- export documentation and labeling support
- mixed-SKU kit assembly

## 6. FAQ

ForgeBase model: `FAQItem`

Planned use:
- 15 to 25 FAQs across sourcing, MOQ, testing, OEM, and logistics
- some FAQs linked directly to products and applications

## 7. Comparisons

ForgeBase model: `ComparisonTopic`

Planned use:
- 6 to 10 high-intent comparison pages
- designed to attract mid-funnel search and lead into category/product pages

## 8. Pages

ForgeBase model: `Page`

Planned page use:
- About
- OEM/ODM
- Quality Assurance
- Download Resources
- Privacy / policy pages if needed for demo completeness

## 9. Assets

ForgeBase model: `ContentAsset`

Planned use:
- spec sheets
- capability brochures
- OEM checklist PDF
- product line cards
- certification documents

## 10. Relationship Plan

Relationships that should exist in the first complete demo load:
- Product -> Application
- Product -> Certification
- Product -> FAQ
- Product -> ComparisonTopic
- Application -> FAQ
- selected alternative-product links

## 11. Seed Build Order

Recommended import sequence:
1. pages and category images if available
2. product categories
3. products
4. applications
5. certifications
6. capabilities
7. FAQs
8. comparisons
9. assets
10. cross-entity relationships
11. publish workflow for public demo visibility

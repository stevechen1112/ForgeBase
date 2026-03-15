# Import Plan

This file explains how the centralized NorthForge demo package should be loaded into ForgeBase.

## Goal

Load a believable, fully linked fictional manufacturer website into ForgeBase so the public site and admin can be demonstrated with realistic business content.

## Source of Truth

All source content and seed data live under:
- `demo/handtool-company/content/`
- `demo/handtool-company/seed/`
- `demo/handtool-company/assets/`

## Recommended Import Order

1. pages.json
2. categories.json
3. products.json
4. applications.json
5. certifications.json
6. capabilities.json
7. faq-items.json
8. comparison-topics.json
9. assets.json
10. relationships.json

## Important Notes

- `products.json` currently uses `category_slug` as a human-friendly reference. The import script should resolve slug -> category_id before product creation.
- `relationships.json` uses business keys like `product_model_number`, `application_slug`, `cert_slug`, and `faq_question`. The import script should resolve these to actual IDs after entity creation.
- all content is authored for locale `en` and published-state demo visibility.
- placeholder asset paths are currently logical references, not uploaded storage URLs yet.

## Required Import Behaviors

### Categories
Create categories first and store a slug -> id map.

### Products
Resolve `category_slug` using the category map before POSTing products.

### Pages
Create Home, About, OEM/ODM, and Contact pages before demo launch.

### Applications / Certifications / Capabilities / FAQ / Comparisons
Create these entities and build lookup maps by slug or question/title.

### Relationships
After all entities exist:
- link product <-> application
- link product <-> certification
- link product <-> FAQ
- link product <-> comparison
- link application <-> FAQ

## Placeholder Asset Strategy

Until actual files are uploaded, the site can still function with logical file references in content JSON. When ready, upload real assets and replace these paths with true R2/public URLs.

## Success Criteria

A successful import should produce:
- non-empty homepage
- clickable category and product pages
- application pages with linked products
- certification pages with supporting credibility
- populated FAQ and comparison sections
- realistic Contact and About pages
- enough content depth for RFQ, download-gate, and demo walkthroughs

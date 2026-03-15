# NorthForge Demo Package Index

## Central Source of Truth

This directory is the single source of truth for the fictional hand tool manufacturer used in ForgeBase demos.

## Current Files

- `01-company-blueprint.md`: business identity, positioning, buyer profile, timeline, and tone.
- `02-site-content-map.md`: navigation, page system, content depth, and product/application architecture.
- `03-content-model-map.md`: mapping between demo content and ForgeBase entities.
- `04-corporate-profile.md`: founder, leadership, phone, address, operational footprint, and public-facing company identity.
- `05-product-master-catalog.md`: detailed product families, model numbers, naming system, and featured product logic.
- `06-applications-and-capabilities.md`: application narratives, capability positioning, and CTA guidance.
- `07-homepage-source.md`: homepage messaging, hero, credibility blocks, and CTA flow.
- `08-about-source.md`: about-page narrative, founder story, operational strengths, and company milestones.

## Build Sequence

1. finalize brand and company profile
2. write page-level source content
3. generate structured seed JSON
4. add placeholder media and PDFs
5. import into ForgeBase and publish

## Current Structured Seed Outputs

- `../seed/categories.json`: 5 published product categories.
- `../seed/products.json`: 32 published products with model numbers and category linkage via `category_slug`.
- `../seed/pages.json`: published Home, About, OEM/ODM, and Contact pages.

## Quality Standard

The target is not generic placeholder copy. The target is a believable export-manufacturer web presence that can sustain:
- homepage credibility
- meaningful product browsing
- realistic application discovery
- persuasive FAQ and comparison content
- strong RFQ and download-gate conversion flows

## Non-Negotiable Detail Standard

The demo company should carry enough operational detail to feel real at first glance.
That includes named leadership, full addresses, phone and email structure, coherent model numbers, export-market logic, and commercially plausible product taxonomy.

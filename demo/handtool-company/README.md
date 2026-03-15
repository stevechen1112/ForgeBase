# Hand Tool Demo Content Package

This folder centralizes all demo content for a fictional export-oriented hand tool manufacturer built specifically for ForgeBase demos.

## Purpose

This package is not a generic placeholder. It is a complete, high-believability B2B manufacturer content system designed to demonstrate ForgeBase's three layers:

1. Capture: product, application, FAQ, comparison, certification, and company pages with real search intent coverage.
2. Intent: clear content depth from exploratory visitors to procurement-ready buyers.
3. Conversion: RFQ, contact, download-gate, and supporting CTA pathways.

## Folder Structure

- `content/`: source-of-truth business narrative, site architecture, and content planning.
- `seed/`: import-oriented structured files for API seeding and content loading.
- `assets/`: future place for brand visuals, certification badges, product placeholder images, PDFs, and diagrams.

## Environment Template

- `.env.gemini.example`: local environment template for Gemini-based image generation.

Use it like this:
1. Copy `.env.gemini.example` to `.env.gemini`
2. Fill in `GEMINI_API_KEY`
3. Keep `.env.gemini` local only and never paste the key into chat or commit it

## Gemini Image Workflow

Minimum demo image generation now uses:
- `assets/generation-jobs.minimum-demo.json`: batch job manifest
- `seed/generate_demo_images.py`: image generation runner

Example dry run:
- `python demo/handtool-company/seed/generate_demo_images.py --dry-run`

Example real generation:
- `python demo/handtool-company/seed/generate_demo_images.py --limit 3`

The script reads `demo/handtool-company/.env.gemini`, sends prompts to Gemini image generation, and writes output files into `demo/handtool-company/assets/generated/`.

## Working Rule

All demo-company data should live here first.
Do not scatter narrative content across random markdown files, shell scripts, or ad hoc JSON blobs elsewhere in the repository.

## Demo Company

- Company name: NorthForge Tools Co., Ltd.
- Positioning: Taiwanese OEM/ODM professional hand tool manufacturer for importers, industrial distributors, and tool brands.
- Export focus: Europe, North America, Middle East, Southeast Asia.
- Core strengths: torque consistency, material control, private-label manufacturing, mixed-volume flexibility, documentation discipline.

## Next Build Stages

1. Finalize the company blueprint and brand voice.
2. Expand the complete site content corpus.
3. Convert the content corpus into seed-ready structured JSON.
4. Add placeholder assets and downloadable PDFs.
5. Load the data into ForgeBase for end-to-end demo use.

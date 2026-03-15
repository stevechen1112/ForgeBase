# Assets Folder

This folder is reserved for all visual and downloadable demo assets for NorthForge Tools Co., Ltd.

Current working files:
- `00-asset-index.md`
- `01-brand-visual-system.md`
- `02-image-shot-list.md`
- `03-image-prompts.md`
- `logo-northforge-primary.svg`
- `logo-northforge-mark.svg`

Planned contents:
- brand logo variants
- factory placeholder images
- product placeholder images
- category hero images
- certification badge images
- downloadable PDF spec sheets
- OEM checklist PDF
- line card PDF

## File Naming Rules

- use lowercase kebab-case
- prefix by asset type when practical
- keep filenames stable because seed files may reference them later

Examples:
- `logo-northforge-primary.svg`
- `category-torque-socket-tools-hero.jpg`
- `product-nf-tw250-main.jpg`
- `cert-iso-9001-badge.png`
- `pdf-oem-checklist-v1.pdf`

## Working Rule

All demo visuals and downloadable files should be stored here or generated here.
Do not mix them into `web/public` or random temporary folders until we are ready to formalize import and deployment paths.

## Current Status

This folder now contains a usable visual foundation for the demo:
- a defined brand system
- a shot list for the full website
- prompt packs for external image generation
- SVG logo assets that can be used immediately in mockups or UI integration

The next production step is to create the minimum demo-ready raster image bundle defined in `02-image-shot-list.md`.

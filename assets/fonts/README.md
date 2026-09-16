# Fonts

The app needs a Cyrillic-capable TTF for PDF export.

At runtime Tablets looks for fonts in this order:
1. `assets/fonts/DejaVuSansCondensed.ttf` (bundled — recommended)
2. Windows system fonts (`arial.ttf`, `calibri.ttf`, `segoeui.ttf`)
3. Fallback to Helvetica (Latin-1 only, Cyrillic will be replaced)

To bundle offline PDF export with Russian text, download
`DejaVuSansCondensed.ttf` (OFL license) from https://dejavu-fonts.github.io/
and place it in this folder. The file is intentionally NOT committed
(see `.gitignore`) to keep the repo small.

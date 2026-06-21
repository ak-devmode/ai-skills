---
name: md2docx
description: "Convert markdown (.md) files to professionally formatted Word documents (.docx) with Padma brand styling, suitable for Google Docs upload. Use this skill whenever the user asks to convert a markdown file to a Word document or Google Doc, generate a .docx from a .md file, or says things like 'make this a docx', 'export to Word', 'Google Doc version of this', 'convert to docx', or 'put this in a Google Doc'. Also trigger when the user uploads a .md file and asks for a .docx output, or when producing a document that should be delivered as .docx from markdown source. Supports a --bilingual mode for two-column Indonesian/English contracts (lifts PASAL/ARTICLE section labels into blue bands, highlights {{merge_fields}}, adds a running contract footer). Trigger on any mention of converting markdown to Google Docs, since the workflow is md to docx to Google Drive upload. Do NOT use for creating Word documents from scratch without a markdown source (use the docx skill instead), or for reading/editing existing .docx files."
---

# Markdown to DOCX Converter

Converts .md files to professionally formatted .docx files using the `docx` npm package (docx-js). Output renders cleanly in Microsoft Word and Google Docs.

Styling matches the md2pdf skill — same Padma brand colors (#505CA0 blue, #E6854B orange), comparable typography and table formatting.

## When to Use

- User uploads a .md file and wants a .docx or Google Doc version
- User asks to "convert to docx", "export as Word", "make a Google Doc of this"
- User has been working on a markdown document and wants a .docx deliverable
- Any markdown file that needs to become a shareable Word/Google document

## How to Use

### 1. Ensure docx is installed

```bash
npm install -g docx
```

### 2. Run the conversion

The converter script ships with this skill at `~/.claude/skills/md2docx/scripts/md2docx.js`. Run it directly — no need to copy it. Since `docx` is installed globally, point Node at the global modules with `NODE_PATH`:

```bash
SCRIPT=~/.claude/skills/md2docx/scripts/md2docx.js

# Standard Padma internal-doc styling
NODE_PATH=$(npm root -g) node "$SCRIPT" input.md output.docx

# Bilingual contract styling (ID/EN two-column agreements)
NODE_PATH=$(npm root -g) node "$SCRIPT" input.md output.docx --bilingual
```

If the output path is omitted, the script uses the input filename with a `.docx` extension. The `.docx` is written to the path you specify (or the working directory) — share that file with the user.

### 3. (Optional) Upload to Google Drive

If the user wants a Google Doc, use the `Google Drive:create_file` tool to upload the .docx. Google Drive auto-converts .docx to Google Doc format with formatting preserved. If the MCP upload fails, instruct the user to drag-and-drop the downloaded .docx into Google Drive.

## What the Script Handles

- **Headers:** H1–H4, styled with brand blue color, bold
- **Body text:** Justified, clean Arial typography
- **Bullet lists:** - and * prefixed items (proper Word numbering, not unicode bullets)
- **Numbered lists:** 1. 2. 3. etc. (proper Word numbering)
- **Checkboxes:** [ ] and [x] items rendered with ☐/☑
- **Blockquotes:** > prefixed blocks, rendered with background shading
- **Tables:** Markdown pipe tables with blue header row, alternating row shading, proper DXA column widths
- **Inline formatting:** **bold**, *italic*, `code`, [links](url)
- **Horizontal rules:** --- or *** rendered as bottom-border paragraphs
- **Header/Footer:** "Padma Medical Group" right-aligned header, centered page numbers in footer

## Bilingual Mode (`--bilingual`)

For two-column Indonesian/English contracts (e.g. WellMed agreements). Tuned to match the `Perjanjian_Kemitraan` ver4 layout. Differences from standard mode:

- **Title block:** the H1 is split on ` / ` into a centered Indonesian line (13pt bold) and English line (11pt bold). Any lines before the first table (draft notes, merge-field legend, `Nomor`) render as centered meta lines.
- **Section-band tables:** in a two-column table whose header row is exactly `BAHASA INDONESIA | ENGLISH`, that language header is dropped. Each body row whose cell begins with a bold section label (`PASAL`, `ARTICLE`, `BAB`, `PARA PIHAK`, `THE PARTIES`, `PENDAHULUAN`, `RECITALS`) has that label lifted into a single dark-blue band spanning both columns, with the remaining text below it in two columns. The ID and EN labels are merged onto one line and the article number is de-duplicated, e.g. `PASAL 12 — … / ARTICLE 12 — …` collapses to `PASAL 12 — {ID title} / {EN title}`. A leading `—`/`–`/`-` separator left behind is stripped.
- **Inline parsing is recursive**, so nested formatting like `**`{{merge}}`**` (bold + monospace + merge field) is handled correctly — the merge field still gets highlighted even inside bold.
- **Other tables** (data tables, signature blocks) keep a normal blue header row.
- **Merge fields:** `{{field}}` and `` `{{field}}` `` render in monospace with **yellow highlight** so none are missed at signing. Works in standard mode too.
- **Colors:** dark blue (`1F4E79`) bands, black 0.5pt grid, no row striping.
- **Footer:** running footer suppressed on page 1; pages 2+ show the Indonesian title (left, derived from the H1) and `Halaman X / Y` (right). No top header.
- **Page:** A4, ~18mm margins (same as standard).

Standalone fully-bold short lines (e.g. `**TANDA TANGAN / SIGNATURES**`) render as centered blue labels.

## Customization

The script uses Padma brand colors by default. To customize, edit the color constants at the top of `md2docx.js`:

```javascript
const BLUE = '505CA0';
const ORANGE = 'E6854B';
const DARK = '2D2D2D';
```

The header text ("Padma Medical Group") can also be changed in the `sections` config near the bottom of the script.

## Limitations

- No image embedding (markdown images are skipped)
- No syntax-highlighted code blocks (code renders in Courier New but without highlighting)
- Complex nested lists may not render perfectly
- Very wide tables may have narrow columns on A4 page — review and adjust if needed
- Google Drive MCP upload may fail on larger files; drag-and-drop upload works as fallback

#!/usr/bin/env node
/**
 * md2docx.js — Convert markdown files to professionally formatted .docx
 *
 * Usage:
 *   node md2docx.js input.md [output.docx] [--bilingual]
 *
 * Modes:
 *   (default)     Padma internal-doc styling: brand blue headers, running
 *                 "Padma Medical Group" header, centered page-number footer.
 *   --bilingual   Bilingual contract styling (ID/EN). Two-column tables where
 *                 the leading section label (PASAL/ARTICLE/PARA PIHAK/etc.) is
 *                 lifted into a dark-blue title band spanning both columns;
 *                 centered bilingual title block; {{merge_fields}} highlighted
 *                 yellow; running footer with the Indonesian title + page
 *                 numbers (suppressed on page 1).
 */

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  PageNumber, TabStopType, TabStopPosition,
} = require('docx');

// ── Mode flag ──
const RAW_ARGS = process.argv.slice(2);
const BILINGUAL = RAW_ARGS.includes('--bilingual');
const ARGS = RAW_ARGS.filter(a => !a.startsWith('--'));

// ── Colors ──
const DARK = '2D2D2D';
const MID = '555555';
const WHITE = 'FFFFFF';
const LIGHT_BG = 'F0F1F8';
const FONT = 'Arial';

const BLUE = BILINGUAL ? '1F4E79' : '505CA0';   // heading / title-band accent
const TBL_HEADER = BLUE;                         // table header / section-band fill
const BORDER_COLOR = BILINGUAL ? '000000' : 'DDDDDD';
const BORDER_SIZE = BILINGUAL ? 4 : 1;           // eighths of a point
const ALT_ROW = BILINGUAL ? 'FFFFFF' : 'F8F8F8'; // bilingual = no row striping

// ── Page setup (A4, ~18mm margins) ──
const PAGE_W = 11906;
const PAGE_H = 16838;
const MARGIN = 1020;
const CONTENT_W = PAGE_W - 2 * MARGIN; // ~9866

// ── Inline parser (shared by body, cells, headings) ──
/**
 * makeRuns — tokenize markdown inline formatting into TextRun[].
 * opts: { size, color, forceBold, white, highlightMerge, codeSize }
 * Handles: ***bi***, **b**, *i*, `code`, `{{merge}}`, {{merge}}, [link](url).
 * Merge fields ({{...}}) render in monospace; highlighted yellow when enabled.
 */
function makeRuns(text, opts = {}) {
  const {
    size = 18, color = DARK, forceBold = false, white = false,
    highlightMerge = true, codeSize,
  } = opts;
  const ctx = {
    size, color, white, forceBold,
    bold: false, italics: false,
    highlightMerge,
    codeSize: codeSize || Math.max(size - 2, 12),
  };
  if (text === null || text === undefined || text === '') {
    return [new TextRun({ text: ' ', font: FONT, size, color: white ? WHITE : color, bold: forceBold })];
  }
  const runs = renderSpan(String(text), ctx);
  return runs.length ? runs : [new TextRun({ text: String(text), font: FONT, size, color: white ? WHITE : color, bold: forceBold })];
}

// Precedence order matters: triple before double; merge/code before plain text.
const SPAN_PATTERNS = [
  { type: 'bi',     re: /\*\*\*(.+?)\*\*\*/ },
  { type: 'bold',   re: /\*\*(.+?)\*\*/ },
  { type: 'ital',   re: /\*([^*\n]+?)\*/ },
  { type: 'cmerge', re: /`(\{\{[^}]+\}\})`/ },
  { type: 'code',   re: /`([^`]+)`/ },
  { type: 'merge',  re: /(\{\{[^}]+\}\})/ },
  { type: 'link',   re: /\[([^\]]+)\]\([^)]+\)/ },
];

function textLeaf(t, ctx) {
  return new TextRun({ text: t, font: FONT, size: ctx.size, color: ctx.white ? WHITE : ctx.color, bold: ctx.bold || ctx.forceBold, italics: ctx.italics });
}
function codeLeaf(t, ctx, isMerge) {
  return new TextRun({ text: t, font: 'Courier New', size: ctx.codeSize, color: ctx.white ? WHITE : ctx.color, bold: ctx.bold || ctx.forceBold, italics: ctx.italics, highlight: (isMerge && ctx.highlightMerge) ? 'yellow' : undefined });
}

/** Recursive inline renderer — descends into bold/italic so nested `{{merge}}` is caught. */
function renderSpan(text, ctx) {
  const runs = [];
  if (!text) return runs;
  let best = null;
  for (const p of SPAN_PATTERNS) {
    const m = p.re.exec(text);
    if (m && (best === null || m.index < best.m.index)) best = { p, m };
  }
  if (!best) { runs.push(textLeaf(text, ctx)); return runs; }
  const { p, m } = best;
  if (m.index > 0) runs.push(textLeaf(text.slice(0, m.index), ctx));
  switch (p.type) {
    case 'bi':     runs.push(...renderSpan(m[1], { ...ctx, bold: true, italics: true })); break;
    case 'bold':   runs.push(...renderSpan(m[1], { ...ctx, bold: true })); break;
    case 'ital':   runs.push(...renderSpan(m[1], { ...ctx, italics: true })); break;
    case 'cmerge': runs.push(codeLeaf(m[1], ctx, true)); break;
    case 'code':   runs.push(codeLeaf(m[1], ctx, false)); break;
    case 'merge':  runs.push(codeLeaf(m[1], ctx, true)); break;
    case 'link':   runs.push(textLeaf(m[1], ctx)); break;
  }
  runs.push(...renderSpan(text.slice(m.index + m[0].length), ctx));
  return runs;
}

// Back-compat wrappers
function parseInline(text) { return makeRuns(text, { size: 18, color: DARK }); }
function parseInlineCell(text, isHeader) { return makeRuns(text, { size: 18, white: isHeader, forceBold: isHeader }); }
function buildHeadingRuns(text, size, color) { return makeRuns(text, { size, color, forceBold: true }); }

/** Extract a leading section label (PASAL/ARTICLE/PARA PIHAK/...) from a cell. */
function extractSectionTitle(cellText) {
  const m = cellText.match(/^\s*\*\*(.+?)\*\*\s*/);
  if (m) {
    const inner = m[1].trim();
    if (/^(PASAL|ARTICLE|BAB|PARA PIHAK|THE PARTIES|PENDAHULUAN|RECITALS)\b/i.test(inner)) {
      const rest = cellText.slice(m[0].length).trim().replace(/^[\u2014\u2013-]\s*/, '');
      return { title: inner, rest };
    }
  }
  return { title: null, rest: cellText };
}

/** Parse markdown table lines into rows of cell strings. */
function parseTableRows(lines) {
  const rows = [];
  for (const line of lines) {
    let l = line.trim();
    if (l.startsWith('|')) l = l.slice(1);
    if (l.endsWith('|')) l = l.slice(0, -1);
    const cells = l.split('|').map(c => c.trim());
    if (cells.every(c => /^[-:]+$/.test(c))) continue; // separator row
    rows.push(cells);
  }
  return rows;
}

const BORDER = { style: BorderStyle.SINGLE, size: BORDER_SIZE, color: BORDER_COLOR };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const CELL_MARGINS = { top: 60, bottom: 60, left: 100, right: 100 };

/** Standard table: blue header row + body rows (used for data/signature tables). */
function buildTable(rows) {
  if (!rows.length) return null;
  const header = rows[0];
  const body = rows.slice(1);
  const colCount = header.length;
  const colWidth = Math.floor(CONTENT_W / colCount);
  const colWidths = Array(colCount).fill(colWidth);
  colWidths[colCount - 1] = CONTENT_W - colWidth * (colCount - 1);

  const tableRows = [];
  tableRows.push(new TableRow({
    tableHeader: true,
    children: header.map((cell, ci) => new TableCell({
      borders: BORDERS, width: { size: colWidths[ci], type: WidthType.DXA },
      shading: { fill: TBL_HEADER, type: ShadingType.CLEAR }, margins: CELL_MARGINS,
      children: [new Paragraph({ spacing: { before: 20, after: 20 }, children: parseInlineCell(cell, true) })],
    })),
  }));
  body.forEach((row, ri) => {
    while (row.length < colCount) row.push('');
    const cells = row.slice(0, colCount);
    const fill = ri % 2 === 0 ? WHITE : ALT_ROW;
    tableRows.push(new TableRow({
      children: cells.map((cell, ci) => new TableCell({
        borders: BORDERS, width: { size: colWidths[ci], type: WidthType.DXA },
        shading: { fill, type: ShadingType.CLEAR }, margins: CELL_MARGINS,
        children: [new Paragraph({ spacing: { before: 20, after: 20 }, children: parseInlineCell(cell, false) })],
      })),
    }));
  });
  return new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: colWidths, rows: tableRows });
}

/** Combine ID + EN section labels into one line, de-duplicating the article number. */
function combineTitle(idTitle, enTitle) {
  if (idTitle && enTitle) {
    const mi = idTitle.match(/^(PASAL|BAB)\s+([0-9IVXLC]+)\s*[\u2014\u2013-]\s*(.+)$/i);
    const me = enTitle.match(/^(ARTICLE|CHAPTER)\s+([0-9IVXLC]+)\s*[\u2014\u2013-]\s*(.+)$/i);
    if (mi && me && mi[2].toUpperCase() === me[2].toUpperCase()) {
      return `${mi[1].toUpperCase()} ${mi[2]} \u2014 ${mi[3]} / ${me[3]}`;
    }
    return `${idTitle} / ${enTitle}`;
  }
  return idTitle || enTitle || '';
}

/** Bilingual prose table: section-label rows become a single blue title band. */
function buildBilingualTable(bodyRows) {
  const colWidth = Math.floor(CONTENT_W / 2);
  const colWidths = [colWidth, CONTENT_W - colWidth];
  const tableRows = [];

  const bandCell = (t) => new TableCell({
    columnSpan: 2, borders: BORDERS, width: { size: CONTENT_W, type: WidthType.DXA },
    shading: { fill: TBL_HEADER, type: ShadingType.CLEAR }, margins: CELL_MARGINS,
    children: [new Paragraph({ spacing: { before: 20, after: 20 }, children: makeRuns(t, { size: 18, white: true, forceBold: true }) })],
  });
  const bodyCell = (t, ci) => new TableCell({
    borders: BORDERS, width: { size: colWidths[ci], type: WidthType.DXA },
    shading: { fill: WHITE, type: ShadingType.CLEAR }, margins: CELL_MARGINS,
    children: [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 20, after: 20 }, children: makeRuns(t, { size: 18, color: DARK }) })],
  });

  for (const row of bodyRows) {
    const idCell = row[0] || '';
    const enCell = row[1] || '';
    const idT = extractSectionTitle(idCell);
    const enT = extractSectionTitle(enCell);
    if (idT.title || enT.title) {
      tableRows.push(new TableRow({ children: [bandCell(combineTitle(idT.title, enT.title))] }));
      tableRows.push(new TableRow({ children: [bodyCell(idT.rest, 0), bodyCell(enT.rest, 1)] }));
    } else {
      tableRows.push(new TableRow({ children: [bodyCell(idCell, 0), bodyCell(enCell, 1)] }));
    }
  }
  return new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: colWidths, rows: tableRows });
}

/** Convert full markdown text to an array of docx elements. */
function mdToChildren(mdText) {
  const children = [];
  const lines = mdText.split('\n');
  let i = 0;
  let seenTable = false;

  while (i < lines.length) {
    const line = lines[i];
    const stripped = line.trim();
    if (!stripped) { i++; continue; }

    // Horizontal rule
    if (/^-{3,}$/.test(stripped) || /^\*{3,}$/.test(stripped)) {
      if (BILINGUAL) { i++; continue; } // table grid separates sections
      children.push(new Paragraph({
        spacing: { before: 80, after: 120 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: BORDER_COLOR, space: 1 } },
        children: [],
      }));
      i++;
      continue;
    }

    // Headers
    const hMatch = stripped.match(/^(#{1,4})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const text = hMatch[2];

      if (level === 1 && BILINGUAL) {
        const parts = text.split(' / ');
        const idLine = parts[0].trim();
        const enLine = parts.slice(1).join(' / ').trim();
        children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40, after: enLine ? 20 : 120 }, children: buildHeadingRuns(idLine, 26, DARK) }));
        if (enLine) children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 }, children: buildHeadingRuns(enLine, 22, DARK) }));
        i++;
        continue;
      }

      const headingMap = {
        1: { size: 28, color: BLUE, before: 240, after: 120 },
        2: { size: 24, color: BLUE, before: 200, after: 100 },
        3: { size: 21, color: BLUE, before: 160, after: 80 },
        4: { size: 19, color: DARK, before: 120, after: 60 },
      };
      const h = headingMap[Math.min(level, 4)];
      children.push(new Paragraph({ spacing: { before: h.before, after: h.after }, children: buildHeadingRuns(text, h.size, h.color) }));
      i++;
      continue;
    }

    // Table
    if (stripped.startsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) { tableLines.push(lines[i]); i++; }
      const rows = parseTableRows(tableLines);
      let tbl;
      if (BILINGUAL && rows.length &&
          /^bahasa indonesia$/i.test((rows[0][0] || '').trim()) &&
          /^english$/i.test((rows[0][1] || '').trim())) {
        tbl = buildBilingualTable(rows.slice(1));
      } else {
        tbl = buildTable(rows);
      }
      if (tbl) {
        seenTable = true;
        children.push(new Paragraph({ spacing: { before: 80 }, children: [] }));
        children.push(tbl);
        children.push(new Paragraph({ spacing: { after: 80 }, children: [] }));
      }
      continue;
    }

    // Blockquote
    if (stripped.startsWith('>')) {
      const quoteLines = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) { quoteLines.push(lines[i].trim().replace(/^>\s?/, '')); i++; }
      for (const ql of quoteLines) {
        children.push(new Paragraph({ indent: { left: 400 }, spacing: { before: 20, after: 20 }, shading: { fill: LIGHT_BG, type: ShadingType.CLEAR }, children: parseInline(ql) }));
      }
      continue;
    }

    // Preamble (bilingual, before first table): center each meta line
    if (BILINGUAL && !seenTable) {
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 40 }, children: makeRuns(stripped, { size: 18, color: DARK }) }));
      i++;
      continue;
    }

    // Standalone fully-bold short line → centered label (bilingual)
    const boldOnly = stripped.match(/^\*\*(.+)\*\*$/);
    if (BILINGUAL && boldOnly && boldOnly[1].length <= 70 && !boldOnly[1].includes('**')) {
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 80 }, children: buildHeadingRuns(boldOnly[1], 22, BLUE) }));
      i++;
      continue;
    }

    // Checkbox items
    const cbMatch = stripped.match(/^-?\s*\[( |x)\]\s+(.+)/);
    if (cbMatch) {
      const box = cbMatch[1] === 'x' ? '\u2611 ' : '\u2610 ';
      children.push(new Paragraph({ indent: { left: 480, hanging: 360 }, spacing: { before: 20, after: 40 }, children: [new TextRun({ text: box, font: FONT, size: 18, color: DARK }), ...parseInline(cbMatch[2])] }));
      i++;
      continue;
    }

    // Bullet list
    const bulletMatch = stripped.match(/^[-*]\s+(.+)/);
    if (bulletMatch) {
      children.push(new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 20, after: 40 }, children: parseInline(bulletMatch[1]) }));
      i++;
      continue;
    }

    // Numbered list
    const numMatch = stripped.match(/^(\d+)\.\s+(.+)/);
    if (numMatch) {
      children.push(new Paragraph({ numbering: { reference: 'numbers', level: 0 }, spacing: { before: 20, after: 40 }, children: parseInline(numMatch[2]) }));
      i++;
      continue;
    }

    // Regular paragraph — collect contiguous lines
    const paraLines = [];
    while (i < lines.length) {
      const l = lines[i].trim();
      if (!l || l.startsWith('#') || l.startsWith('>') || l.startsWith('|') ||
          /^[-*]\s+/.test(l) || /^\d+\.\s+/.test(l) ||
          /^-{3,}$/.test(l) || /^\*{3,}$/.test(l) ||
          /^-?\s*\[[ x]\]/.test(l)) break;
      paraLines.push(l);
      i++;
    }
    if (paraLines.length) {
      children.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 20, after: 80 }, children: parseInline(paraLines.join(' ')) }));
    }
  }
  return children;
}

/** First H1's Indonesian half (text before " / ") — used for the running footer. */
function getDocTitle(md) {
  for (const ln of md.split('\n')) {
    const m = ln.match(/^#\s+(.+)/);
    if (m) return m[1].split(' / ')[0].trim();
  }
  return '';
}

// ── Main ──
async function convert(inputPath, outputPath) {
  if (!outputPath) {
    const base = path.basename(inputPath, path.extname(inputPath));
    outputPath = path.join(path.dirname(inputPath), base + '.docx');
  }

  const mdText = fs.readFileSync(inputPath, 'utf-8');
  const children = mdToChildren(mdText);
  if (!children.length) children.push(new Paragraph({ children: [new TextRun({ text: '(empty document)', font: FONT, size: 18 })] }));

  const numbering = {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 260 } }, run: { font: FONT, size: 18, color: DARK } } }] },
      { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 260 } }, run: { font: FONT, size: 18, color: DARK } } }] },
    ],
  };

  const pageProps = { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } };

  let section;
  if (BILINGUAL) {
    const titleBhs = getDocTitle(mdText);
    const runningFooter = new Footer({
      children: [new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
        children: [
          new TextRun({ text: titleBhs, font: FONT, size: 15, color: MID, italics: true }),
          new TextRun({ text: '\t', font: FONT, size: 15 }),
          new TextRun({ text: 'Halaman ', font: FONT, size: 15, color: MID }),
          new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: MID }),
          new TextRun({ text: ' / ', font: FONT, size: 15, color: MID }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 15, color: MID }),
        ],
      })],
    });
    const emptyFooter = new Footer({ children: [new Paragraph({ children: [] })] });
    section = {
      properties: { page: pageProps, titlePage: true },
      footers: { default: runningFooter, first: emptyFooter },
      children,
    };
  } else {
    section = {
      properties: { page: pageProps },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: 'Padma Medical Group', font: FONT, size: 14, color: MID, italics: true })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Page ', font: FONT, size: 14, color: MID }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 14, color: MID })] })] }) },
      children,
    };
  }

  const doc = new Document({
    styles: { default: { document: { run: { font: FONT, size: 18, color: DARK } } } },
    numbering,
    sections: [section],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  console.log(`\u2713 ${inputPath} \u2192 ${outputPath}${BILINGUAL ? '  [bilingual]' : ''}`);
  return outputPath;
}

if (ARGS.length < 1) {
  console.log('Usage: node md2docx.js input.md [output.docx] [--bilingual]');
  process.exit(1);
}
convert(ARGS[0], ARGS[1]).catch(err => { console.error('Error:', err.message); process.exit(1); });

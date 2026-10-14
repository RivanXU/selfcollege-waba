<!-- Copyright (c) 2026 RivanXU. SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0. See LICENSE and NOTICE. -->

# PDF layout and renderer contract

Use this reference when authoring the study guide or slide companion. The renderer composes locally authored content; it does not translate, reconstruct slide layouts, verify teaching claims, or solve homework. Prepare source-backed content first and visually inspect the final PDFs.

## Two distinct reading experiences

The **study guide** teaches one connected learning unit at a time. Use the chain: question -> necessary prerequisite -> definitions -> why the equation applies -> one justified change per line -> worked calculation -> interpretation -> linked homework. A new symbol receives its definition beside the first equation that uses it. Put a homework question, its source location, the relevant lesson, each solution step and a check together. Explicitly distinguish source statements, instructor remarks and added explanations.

The **slide companion** preserves a page-for-page pair of slides. Above the annotation band, the source page and translated page have identical viewport dimensions and exactly the same scale. Translation belongs in the source slide's corresponding text boxes, with the same hierarchy, graphics, equation positions and reading order. Vocabulary, prerequisites, instructor remarks, homework links and explanatory additions all belong in a full-width band below both slides. The translation page must be prepared before using this compositor, preferably by editing a duplicate of the original slide deck and exporting it. A matching page size alone does not prove matching layout or complete translation.

If editable slides are unavailable, manually reconstruct a faithful translation using positioned text and source graphics, then compare every page visually. The bundled renderer does not automatically mask source text, reconstruct text boxes, translate diagram labels, or verify an independently supplied translation PDF. Record unresolved mismatches instead of claiming fidelity.

## Readable knowledge blocks

- Study-guide defaults: A4 portrait, 47-point margins, 11.5-point body with 18.5-point leading; 13.2-point section headings; 21-point page titles; 15-point mathematics. Display math is about 1.3 times the body size, with 3-point vertical padding on each side. Symbol legends use math at 1.2 times their table text size. Fractions require more physical height than a single text line; give them that height without enlarging every glyph.
- Group a connected concept under one heading. Keep its prerequisites, derivation, symbol definitions, worked example and interpretation together or continue onto an explicitly titled next page. Leave 16 points between concept groups.
- A page can contain multiple related blocks, but its structure follows the knowledge dependency, not the source slide's line breaks. Avoid paragraphs that cram several unexplained operations into one sentence.
- Slide-companion defaults: 1190.551 x 841.89 points, 36-point outer margins, a 32-point column gap and a 200-point annotation band. Both complete pages fit the available viewports at one shared scale. Increase the output page height or annotation band for more notes; avoid making the text smaller.
- Body, vocabulary tables, equations, captions and notes retain distinct roles. Source PDF text and graphics remain vector where they were vector; scanned source pages remain scans.
- Judge mathematical size against neighboring body text at actual reading scale. Use a consistent moderate formula size throughout a guide; split long expressions instead of enlarging them into a headline or shrinking one formula to fit. A lecture's preserved source panels retain the source's own typography and a shared panel scale.
- Colors are secondary: navy `#17334D`, teal `#117E82`, ink `#263746`, muted `#607485`, light blue `#EDF4FA`, light green `#ECF7F5`, amber `#FFF5E9`. Source labels and warning text convey the meaning without color.

## Exact-layout paired-PDF input

The command-line entry point is:

```bash
python3 scripts/render_study_pdfs.py --spec /absolute/path/content.json --output-dir /absolute/path/output
```

Install the declared Python dependencies from `requirements.txt`. The bundled Noto Sans SC font covers English, Chinese and some other scripts; a course may pass `--font /absolute/path/covered.ttf`. Coverage is checked before text is drawn. Font coverage alone does not establish correct shaping or text direction. The bundled text path rejects right-to-left scripts; use a shaping-aware engine and verify its local PDF for those languages or other scripts requiring complex shaping. Paired source/translated PDFs may come from that engine. The math renderer uses its own mathematical fonts.

A paired companion requires `source_pdf` and `translated_pdf`. Both PDFs must contain the same number of pages, and each paired visible page must have the same physical dimensions after rotation and PDF UserUnit normalization, within 0.01 point. The `bilingual` entries cover every source page exactly once in order, from 1 to N. This minimal specification makes one companion and one guide:

```json
{
  "course_code": "COURSE-101",
  "course_name": "Example course",
  "lecture": "Lecture 1",
  "file_stem": "lecture-01",
  "source_pdf": "/absolute/path/source-slides.pdf",
  "translated_pdf": "/absolute/path/translated-slides.pdf",
  "bilingual_mode": "paired_pdf",
  "bilingual_layout": {
    "page_width": 1190.551,
    "page_height": 841.89,
    "annotation_height": 200
  },
  "bilingual": [
    {
      "source_page": 1,
      "title": "A matched pair of slides",
      "terms": [["Ratio", "A comparison obtained by division"]],
      "notes": [{"label": "Prerequisite", "text": "Explain the assumed concept here.", "source": "Added explanation; source slide 1"}],
      "transcript": [{"label": "Instructor remark", "text": "A verified remark from the provided recording.", "source": "Recording 03:14"}],
      "homework": [{"label": "Practice link", "text": "Question 1 uses this ratio; its complete worked solution is on guide page 2.", "source": "Problem sheet, question 1"}],
      "guide_pages": "1-2"
    }
  ],
  "guide": [
    {
      "title": "Understand a ratio before calculating",
      "subtitle": "One learning unit",
      "source": "Source slide 1; problem sheet question 1",
      "blocks": [
        {
          "type": "concept",
          "title": "From a comparison to an equation",
          "blocks": [
            {"type": "text", "text": "Introduce the question and necessary prerequisite."},
            {"type": "formula", "latex": "r=\\frac{a}{b}", "reason": "Divide the quantity being compared by its reference quantity. The reference must be nonzero.", "symbols": [["r", "The ratio"], ["a", "The quantity being compared"], ["b", "The nonzero reference quantity"]]},
            {"type": "box", "label": "Check understanding", "text": "Explain how the equation answers the original question.", "tone": "green"}
          ]
        }
      ]
    }
  ]
}
```

The example's transcript entry is schema illustration only. Omit that field when no recording or transcript was supplied. The example assumes a one-page source; add one `bilingual` entry per actual source page. Either `guide` or `bilingual` can be omitted to produce only the other artifact.

`title` is the preferred page heading. `title_zh` and `title_en` are accepted as heading aliases; they do not reconstruct a translated slide. `terms` contains pairs of term and explanation. `notes`, `transcript` and `homework` contain entries with `label`, `text` and optional `source`. All are rendered only in the bottom band. Long notes must move to a cited guide page or receive more physical page space.

## Mathematics with genuine fraction bars

A formula block requires `latex` and `reason`. Use `\frac{numerator}{denominator}` for division, braces for multi-character scripts and a separate block for each derivation step. The renderer does not accept a `formula.text` field and slash fractions. It draws supported MathText LaTeX as PDF vector outlines, including actual fraction rules, superscripts and subscripts. Text font failures do not permit deleting symbols.

The fraction rule applies to displayed mathematical division such as `a/b` or `dy/dx`. Preserve actual programming operators, file paths, unit labels and structural slash notation from the source. Ordinary prose/code outside formula blocks is untouched. Inside a formula, mark a literal unit/code/text region explicitly, for example `\mathrm{m/s}`, `\mathtt{a/b}` or `\text{path/to/file}`. A structural slash can be written as `\text{/}`. These literal regions retain their slash; they must not be used to disguise a displayed fraction.

```json
[
  {"type":"formula","label":"Step 2: substitute the values","latex":"r=\\frac{12}{4}","reason":"Replace the numerator and denominator using the quantities identified in the question.","symbols":[["r","A unitless ratio because both quantities have the same unit"]]},
  {"type":"formula","label":"Step 3: evaluate the division","latex":"r=3","reason":"Twelve divided by four equals three. The compared quantity is three times its reference quantity."}
]
```

The first column of `symbols` is a LaTeX math expression, also rendered as a vector formula. The second column is explanatory text. Define every newly introduced symbol nearby, including its units, role, index and relevant domain. The renderer cannot decide whether those definitions or the mathematical claim are correct; the author performs that check.

MathText supports a useful LaTeX subset rather than a full TeX installation. Unsupported commands, warning-producing expressions and over-wide equations fail. Rewrite an equivalent supported expression or provide a verified vector source crop; never silently replace it with a slash or shrink it to fit. An `image` block is an explicit image fallback and cannot be described as vector mathematics. Long derivations use one step per formula block. Supply a readable verbal explanation as well as the formula because these PDFs are not tagged accessible documents and mathematical outlines are not searchable text.

The bundled engine handles common fractions, ordinary/partial derivatives, integrals, sums, roots, logarithms and mathematical alphabets. Matrix, cases and aligned environments such as `\begin{pmatrix}`, `\begin{cases}` and `\begin{aligned}` require another capable engine; they are not supported by the bundled formula block. Use separate formula blocks for an aligned derivation. For a new matrix or piecewise expression, typeset it with an available full TeX-compatible engine, export a local vector PDF, and embed its verified page/region with `source_crop`. Keep the derivation reason and symbol legend immediately beside/below that crop as ordinary guide blocks. If such an engine is unavailable, report that precise limitation rather than claiming the expression was rendered. A source crop of an existing source formula is useful only when it actually contains the required expression.

For example, after authoring and verifying a tightly bounded local PDF of a matrix equation, include these neighboring blocks on the same guide page:

```json
[
  {"type":"source_crop","source_pdf":"/absolute/path/authored-matrix-equation.pdf","page":1,"height":95,"caption":"Tutor derivation, step 3; vector equation authored with a full TeX engine"},
  {"type":"text","text":"Why this step follows: collect the two simultaneous linear equations into one matrix equation. The first row reproduces the first equation; the second row reproduces the second."},
  {"type":"table","header":["Symbol","Meaning in this step"],"rows":[["A","The 2 by 2 matrix of fixed coefficients"],["x","The column vector of the two unknowns"],["b","The column vector of given right-hand sides"]]}
]
```

Use a tight exported PDF page or an explicit verified `clip` so the formula remains readable. A local raster fallback instead uses `{"type":"image","path":"/absolute/path/verified-equation.png","height":95,"caption":"Explicit raster equation fallback"}` and requires resolution/visual review; it cannot carry a vector claim.

## Guide blocks and bounded pagination

Each `guide` entry describes one explicit page. Supported blocks are:

| Block | Content |
| --- | --- |
| `concept` | `title` and nested `blocks`, with a visible inter-group gap |
| `heading`, `text`, `small` | `text`, using restrained markup |
| `formula` | `latex`, required `reason`, optional `label` and `symbols` |
| `box` | `label`, `text`, optional tone `green`, `blue` or `amber` |
| `table` | optional `header`, required `rows`, optional positive column `widths` |
| `image` | local `path`, optional positive maximum `height` and `caption` |
| `source_crop` | local `source_pdf`, 1-based `page`, optional `clip`, positive maximum `height` and `caption` |

Overflow raises an error. Split at a pedagogical boundary and add an explicit continuation page with the previous step and next question. The renderer does not delete text, shrink body fonts, truncate notes or silently add pages that would break page references.

`source_crop.clip` is `[left, top, right, bottom]` in physical PDF points, measured from the top-left corner of the rotated visible source page. It must stay within that page. Cropping changes the visible region, but does not remove hidden material and must never be used for privacy redaction. Composition omits interactive actions and links. A visible non-link annotation causes an explicit error: flatten legitimate handwriting, highlights, comment appearances, stamps, or form values into a separate copy with a capable PDF tool, then compare the rendered copy with the original before composition. Do not discard instructor annotations to bypass the check. Hidden/invisible annotations are omitted.

Text accepts simple attribute-free `<b>`, `<strong>`, `<i>`, `<em>`, `<u>`, `<strike>`, `<sub>`, `<super>`, `<sup>` and `<br/>`. Escape a literal ampersand or less-than sign as `&amp;` or `&lt;`. Images use local `image` blocks; embedded HTML resources and remote image URLs are rejected.

## Explicit reflow fallback

A translation array is not an exact-layout slide. If a reader intentionally requests a reflowed text companion, specify `"bilingual_mode": "reflow"`, omit `translated_pdf`, and give each page a `translation` array. Every output page displays **Reflow fallback - layout differs from source** inside the right viewport. Both viewport boundaries remain equal, and supplementary notes remain below both. This fallback cannot satisfy a request for mirrored PPT layouts and must not be used without a conscious choice.

## Course-owned labels and style overrides

Defaults and output filenames are English: `<file_stem>_study-guide.pdf` and `<file_stem>_slide-companion.pdf`. Actual teaching and translation language follow the learner's course preference, independently of public package naming.

Use `labels` to change `source_heading`, `translation_heading`, `terms_heading`, `symbol_heading`, `symbol_meaning_heading`, `guide_name`, `bilingual_name`, `guide_header`, `bilingual_header`, `source_footer` or `guide_reference_footer`. Set the two symbol headings in the learner's chosen language, independently of the public package language. Header labels follow the output name when omitted. Footer placeholders are restricted to `{filename}`, `{page}` and `{pages}` in their respective fields. Names must be plain filename stems; the two outputs must have distinct names. Headers and footer pairs are measured before drawing; shorten metadata or use compact page ranges when they cannot fit, keeping the full title and detailed locators in the page body or annotation band.

Use `--style /absolute/path/style-overrides.json` for a course-owned JSON containing only known keys from `assets/style_tokens.json`. Colors are six-digit `#RRGGBB`; dimensions are finite positive numbers; leading is at least body font size. Guide `formula_size` must be at least the body size and no more than 1.5 times it; the default is about 1.3 times. This keeps equations readable without turning them into headlines. Overrides preserve bundled assets. Do not lower readable sizes to force more content onto a page.

## Safety and verification

All referenced input paths must name existing local files. Outputs are checked against referenced PDFs, images, fonts, content specifications, style overrides, the renderer and bundled style tokens, including hard-link aliases. All requested artifacts are staged before publication; a rendering error preserves existing deliverables, and a publication failure rolls back files already replaced. A process kill or machine failure during multi-file publication is outside this rollback guarantee.

The success response contains output paths, page counts and a companion positioning report. For every page, the report records source dimensions, the shared scale, both viewports and the bottom annotation band. It explicitly states that geometric checks are not proof of layout/content fidelity. Keep this report with course QA evidence when useful.

Run the regression suite with `python3 scripts/test_render_study_pdfs.py`. It checks page order/count, dimension mismatch, rotation/UserUnit handling, actual identical merge scales, labeled fallback, fraction-bar and script geometry, vector drawing, overflow, input protection and rollback.

Before delivery, render every final page to an image and inspect it at reading size. Confirm the pair's text boxes, diagrams, equation placements, completeness and reading order; confirm notes are exclusively below both pages; check each symbol, derivation reason, homework question, solution and cross-reference. Text extraction or matching page counts alone cannot establish visual fidelity. Record the final filenames, page counts, reviewed images and remaining limitations in the course workspace.

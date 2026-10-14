<div align="center">

# selfcollege-waba

### Follow the lecture's reasoning. Learn to solve the next problem.

A university learning skill for connected explanations, faithful slide companions, and homework taught inside the lesson.

**[Download the skill](https://github.com/RivanXU/selfcollege-waba/releases/latest/download/selfcollege-waba.zip)** · **[Explore the examples](#see-the-output)** · **[Get started](#get-started)**

</div>

Slides compress an argument into a few lines. selfcollege-waba expands that argument into a lesson: what the previous idea established, why the next idea is needed, what each symbol means, and how the reasoning becomes a solution.

The skill works with quantitative courses, humanities, programming, and practical coursework. It follows the source lecture's order while grouping consecutive slides into coherent knowledge modules. Teaching language, starting knowledge, and output format follow the learner's needs. Repository documentation and filenames are English. The original public example includes an English-to-Chinese translation.

## See the output

The original university example follows one complete chain: spring and damping forces, the differential equation, characteristic roots, a real motion determined by initial conditions, and a worked parameter-change problem. The response graph makes the distinction between oscillation and its decaying envelope visible. All slides, numerical conditions, questions and figures were independently authored for this repository; no real course or learner materials are included.

### Matching English and Chinese slides

The translation preserves the corresponding text boxes, mathematical notation, plotted curves, axes and values. Added vocabulary, foundation notes and practice references sit below both complete slide panels.

[![Original English and Chinese oscillator slides with matched formulas and a response graph](examples/previews/comparison.png)](examples/previews/comparison.png)

**[Open the slide companion](examples/slide-companion.pdf)** · [Original slides](examples/source-slides.pdf) · [Chinese translation](examples/translated-slides.pdf)

### Connect the initial conditions to the solution

This is an actual page from the study guide. It connects the general motion to initial displacement and velocity, then explains the envelope and the numerical case. Important steps receive mathematical structure and reasons; routine arithmetic stays concise.

[![Deriving the initial-condition constants and envelope in the complete study guide](examples/previews/explanation.png)](examples/previews/explanation.png)

### Read the complete problem and choose the method

The full four-part question, its modeling conditions and method links appear together. Pages 8–10 solve every part, including a changed damping coefficient; page 11 explains limits and transfer.

[![Complete original oscillator problem with prerequisite links and the start of its solution](examples/previews/practice.png)](examples/previews/practice.png)

**[Open the beginner study guide](examples/beginner-study-guide.pdf)**

The eleven-page guide expands three compact slides into connected knowledge blocks. Its length follows the learning content and readability. The desktop previews are rendered directly from the actual PDFs at 216 or 288 dpi; click an image for full resolution. These examples demonstrate named behavior without claiming every subject or language has been tested.

## What it does

| Learner's need | Skill behavior |
| --- | --- |
| "I read every page but lost the thread." | Read the whole lecture first, map its question, and explain consecutive modules in source order with explicit transitions. |
| "The formula skips steps." | Explain foundations, introduce symbols nearby, and typeset each transformation with its reason, conditions, and interpretation. |
| "These numbers all look the same." | Separate assumptions, coefficients, intermediate calculations, results, proportions, and changes; explain when examples reset to baseline. |
| "I need an exact slide translation." | Prepare a matching translated slide/page set, preserve object layout, pair equal panels, and put all extra notes below. |
| "I cannot start the homework." | Include the supplied question and subparts inside the guide, link its prerequisites, justify the method, and walk through the solution. |
| "The instructor explained more than the PPT." | Add necessary tutor foundations, and align supported transcript remarks to the correct slides/modules. |
| "My course is not mathematical." | Explain claims, evidence, code state, procedures, or evaluation using the same connected reasoning standard. |
| "Continue where I left off." | Read the accessible course record, verify the source, and continue actual progress without treating a generated guide as mastery. |

The normal lecture pack contains two PDFs: a **slide companion** with one page per
original slide and a **beginner study guide** organized into connected modules.
Focused questions, homework-only requests and other formats follow the requested
scope. A comfortable conversational teaching style also works inside a PDF; it
does not cancel the requested artifacts. Keep equations moderate and connected
to their explanations. Use words or a light table for obvious small datasets;
add a chart only when it clarifies a useful relationship, comparison, trend or
mechanism, or the learner requests one.

## Get started

### Install locally

Download and extract the package, and keep the complete `selfcollege-waba` folder together.

For one course/project place it at:

```text
.agents/skills/selfcollege-waba/SKILL.md
```

For user-wide discovery use `~/.agents/skills/selfcollege-waba/`. Keep one installation per intended scope. In Codex invoke `$selfcollege-waba`; consult the [official skill documentation](https://learn.chatgpt.com/docs/build-skills) for current discovery and installation behavior.

A skill-compatible application may have its own folder/ZIP import interface. If yours has no skill installation, copy the [portable study prompt](references/master-prompt.md) and provide your materials. Local installation does not automatically synchronize the package or course history to another device or cloud project; verify the destination's actual import and persistence behavior.

### Start a lesson

> Use $selfcollege-waba to help me study this lecture. Teach in my preferred language and retain original technical terms. Follow the PPT's order, explain consecutive knowledge modules, show every derivation step with proper fractions, and put the full homework questions and guided solutions in the study guide. Make a faithful slide companion with all extra notes below the matching slide panels.

Course, lecture scope, language, and relevant starting knowledge are enough. Personal background is optional. Slides alone can start the lesson; a transcript or homework file can be added later.

## Rendering and reproducibility

The bundled renderer composes **an original PDF plus an already translated PDF** into matched panels. It does not automatically translate, OCR, or reconstruct slides. Native PPTX translation and PDF/scan reconstruction follow the [slide translation protocol](references/slide-translation.md), using available tools and page-by-page review.

Guide formulas use Computer Modern vector mathematical rendering with genuine fraction bars, scripts, and roots. Short mathematical runs stay within their sentences at body size, including table cells and notes. Displayed guide equations use a moderate 13.2-point default beside 11.5-point body text; full-size fraction operands and smaller true scripts preserve their hierarchy. The renderer supports a MathText subset of LaTeX; unsupported commands fail visibly. Use another capable engine for expressions outside that subset. Mathematical vector outlines are sharp but are not searchable or tagged accessible math; retain the editable equation source for reuse. General text remains selectable.

Set up an isolated Python 3.10+ environment and install [requirements.txt](requirements.txt). Rebuilding demonstration previews also requires Poppler's `pdftoppm` executable (for example, install Poppler through your system package manager). Liberation Sans and Noto Sans SC fonts are bundled and embedded in the public example; other scripts/fonts or right-to-left layout may need a different renderer and validation. No API key is required by the package itself.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_examples.py
.venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Input structure, formula blocks, and rendering limitations are documented in [pdf-style.md](references/pdf-style.md). Translation, educational reasoning, and visual fidelity require review; automatic count/dimension checks do not prove content accuracy.

To verify a downloaded bundle:

```bash
python3 scripts/verify_package.py
```

To build a distributable ZIP:

```bash
python3 scripts/build_package.py --output-dir ../dist
```

Verification checks required entrypoints, unlisted package additions, and checksums. Declared development/runtime directories such as `.git` and `.venv` are excluded. The manifest is not a signature or proof of origin. Obtain the package from the author's repository.

## Privacy, evidence, and continuity

The package contains no author server, telemetry, or upload mechanism. Learner files, transcripts, answers, and course records stay outside the skill in the learner's chosen course space. The AI application's own data handling depends on that application's settings and terms.

Source and translated content, classroom evidence, tutor foundations, derivations, practice, and uncertainty are labeled separately. Important missing basics are taught where needed; teacher emphasis and assessment claims require evidence. Original materials are preserved. Follow-up learning depends on a record actually saved and accessible to the next conversation.

## License and feedback

Copyright (c) 2026 RivanXU. Original project files use [PolyForm Noncommercial 1.0.0](LICENSE). Noncommercial use, modification, and sharing are subject to that license and the required [NOTICE](NOTICE). Commercial use outside its permissions needs separate authorization. This is a source-available project with noncommercial conditions; third-party components retain their own licenses as described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Course materials retain their original rights and stay in private course workspaces. Public demonstrations use independently authored neutral fixtures, never real course slides, guides, recordings or disguised derivatives. Modified copies do not imply author endorsement.

Report reproducible issues through [GitHub Issues](https://github.com/RivanXU/selfcollege-waba/issues), with the requested outcome and a minimal independently authored neutral reproduction. Do not attach private course files, screenshots, links, identifiers or metadata. Licensing questions can use the author's public [GitHub profile](https://github.com/RivanXU).

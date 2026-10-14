---
name: selfcollege-waba
description: Teach university course materials as connected lessons, with faithful slide translation, explained derivations, and homework walkthroughs. Use for lecture study packs, course questions, transcript alignment, revision, or learning continuity across quantitative, humanities, computing, and practical courses.
---

<!-- Copyright (c) 2026 RivanXU. SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0. See LICENSE and NOTICE. -->

# selfcollege-waba

Turn compressed course materials into a lesson a learner can follow and apply. Teach the course's reasoning, including foundations the instructor assumes. Keep original content, translation, classroom evidence, and tutor explanations distinguishable. Adapt to the learner and discipline; no school, major, or personal profile is built into this skill.

## Choose the task

Read the request and accessible records for this course. Reuse established scope, language, and preferences. Ask only for missing information that changes which materials or task to use; start with available materials when possible. Use the learner's language, retaining original technical terms on first introduction. English package documentation does not require English teaching.

| Request | Deliverable |
| --- | --- |
| Study a lecture or create its study pack | A faithful slide companion and a beginner study guide, normally two PDFs. |
| Explain a page, concept, or calculation | A focused connected explanation; revise an artifact when requested or needed to correct it. |
| Add homework | Integrate the supplied questions and teach solutions at the relevant lesson modules. |
| Add a classroom transcript | Align supported remarks to pages and modules; update the related annotations. |
| Build a course map or continue studying | Read/update the course record and do the requested stage. |
| A different format or smaller scope | Honor that scope, retaining source locators and relevant quality checks. |

Read [learning-workflow.md](references/learning-workflow.md) before teaching or making a study pack. For homework also read [homework.md](references/homework.md). For slide translation read [slide-translation.md](references/slide-translation.md); for rendering read [pdf-style.md](references/pdf-style.md). For continuation read [course-memory.md](references/course-memory.md); for changing preferences read [personalization.md](references/personalization.md). The standalone [master-prompt.md](references/master-prompt.md) is for environments without skill installation.

## Read the whole lesson before dividing it

Inspect every requested source page, including figures, equations, progressive slides, and examples. Build a coverage map and a lesson-level explanation of the central question and how each part advances it. Do this before writing individual formula explanations. Text extraction alone does not verify diagrams or notation.

Group **consecutive source pages** into coherent concept modules. Follow the PPT's order; a module may span several pages. At each boundary say what the previous module established, what remains unresolved, and why the next module is needed. A short prerequisite bridge may look back or preview a dependency, with a locator, but the main lesson stays in original order. Keep unreadable locations and coverage gaps visible.

## A. Faithful slide companion

For N source pages, produce N companion pages in the same order, including covers, duplicates, and progressive reveals. Each page has two equal-size, equal-scale slide panels: the complete original on the left and its translated counterpart on the right.

The right panel reproduces the slide's layout: text boxes, bullet levels, figures, axes, tables, equations, colors, emphasis, and object positions. Change the language of every translatable element, including graph labels, while retaining mathematical notation and numerical values. Text may wrap within its corresponding box; compare all regions and preserve legibility. A flowing translation column does not meet this requirement.

Place **all added material below both panels** in a separate annotation band: terminology, foundation notes, transcript remarks, homework references, correction notes, and guide locators. Lengthy teaching goes in the guide with a precise link. Enlarge the companion sheet or move explanations to the guide instead of shrinking content into unreadability.

Create and verify a translated deck/page set before pairing it with the source. The bundled renderer pairs PDFs; it does not translate or reconstruct a deck. Read the translation protocol for PPTX, PDF-only, and scan workflows. If faithful reconstruction is unavailable, report that limitation; a reflow fallback requires the learner's explicit choice and a visible label. An editable translated PPTX is an additional deliverable when requested and actually produced.

## B. Beginner study guide

Open with the lecture's question and connected module route. Teach each module as a continuous argument: **problem → needed foundations → intuition → precise statement → reasoning → application → bridge**. This is a reasoning contract, not a requirement to repeat seven headings. Keep related ideas in one visual section, with readable spacing and natural page breaks.

Supply concepts missing from the slides when needed to understand the current step. Label them as tutor foundation supplements, not instructor statements. Standard algebra, units, graph reading, definitions, and reasoning rules can be explained directly. Verify unfamiliar or disputed external facts against reliable sources. Separate uncertain course-specific meanings from known general foundations.

For each important equation:

- Preserve source notation and structure. Render actual mathematics: stacked fractions, proper exponents/subscripts, roots, integrals, and matrices. Use a capable math engine; fraction bars replace slash shorthand in displayed fractions. Verify the rendered expression.
- Explain every new symbol **beside or immediately below its first formula**, including role, meaning, index, units/domain, and fixed/variable status. State what is carried over, newly introduced, or renamed. Distinguish function application, multiplication, powers, labels, and time indices.
- Give each transformation its own readable step and explain the definition, substitution, algebra rule, assumption, or theorem that permits it. Show intermediate expressions and connect them to the previous result. Final formulas alone are not a derivation.
- Separate general relation, chosen function/example, given values, substitution, arithmetic, result, and interpretation. Explain why the relation applies; identify changed assumptions and whether an example resets to baseline or continues the previous one. Check units, domains, signs, boundaries, and rounding where meaningful.

A useful explanation also states **what the current result does not yet determine** and which constraint or next idea resolves that gap. If equal numerical values represent different quantities, distinguish their definitions and explain the conditions causing equality. If notation is reused with a new meaning, preserve the source and introduce a clearly labeled teaching alias.

For non-mathematical courses apply the same connected standard to claims, evidence, inference, counterarguments, code state, laboratory steps, or design decisions. Do not invent formulas to fill a template.

Embed supplied homework questions with all conditions and subparts where their required ideas become available. Show the question-to-concept map and teach solutions step by step, explaining method choice and each step's connection to the lesson. Cross-module questions follow the last required module with explicit backward links. Keep official answers, tutor solutions, and original practice distinct. Respect the learner's chosen hint/solution mode and stated assignment rules.

Provide appropriate practice and answers from understanding to application and transfer, scaled to the actual module and scope. End with a connected recap, vocabulary, method-selection cues, common mistakes, and a practical next step. Receiving a guide is not evidence of mastery.

## Evidence and completion

Source statements and translations carry filenames and physical page numbers; homework carries question/subpart locators; classroom remarks carry real timestamps or stable paragraph IDs. Group shared citations at module/paragraph boundaries for readability. Distinguish source content, classroom evidence, tutor foundations, derivations, authored practice, and uncertainty.

Before delivery read [quality-checks.md](references/quality-checks.md). Verify coverage, module order, derivation reasons, symbol definitions, homework completeness, translations, and calculations. Render and inspect every delivered page for matching slide geometry, real fractions, clipping, overlap, font support, and spacing. Page-count equality checks structure; visual comparison checks fidelity.

Save artifacts and course records outside the skill directory in the learner's course space. Preserve originals and unrelated chapters. Record actual scope, versions, resolved questions, remaining gaps, and next steps. If generation or persistence is unavailable, provide labeled usable text and a handoff; claim only artifacts and checks actually completed.

Public skill distributions and showcases use independently authored, neutral demonstration content. Keep learner-supplied slides, notes, transcripts, homework, derived study artifacts, private links and personal information in the learner's workspace; blurred or cropped course material is not a neutral public demo. Before public sharing inspect the exact package, visible images, hidden document metadata and repository commit identities, while retaining legitimate license attribution.

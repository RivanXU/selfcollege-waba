<!-- Copyright (c) 2026 RivanXU. SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0. See LICENSE and NOTICE. -->

# Learner preferences

Use the request and the current learner's accessible course record. Ask about language, scope, or starting knowledge only when missing information materially changes the task. School, major, and identity are optional; a slide cover identifies its source, not the learner's enrollment. Start with relevant foundations when background is unknown and adapt to actual questions.

Priority: current explicit request → course preferences → learner-wide preferences → skill defaults. A one-time choice stays local; "this course" updates this course; "all my courses" updates this learner's preferences. Only an explicit skill-edit request changes the installed package.

Use the learner's chosen language. By default follow the language of their request and retain original technical terms with translations on first use. Support single-language teaching, any supported language pair, or original-plus-annotation when no translation is useful. Package documentation and filenames are English; learner output is not forced into English.

Adjust pacing, prerequisite depth, answer/hint mode, accessibility needs, colors, and output format without weakening source fidelity or reasoning. Necessary bilingual layout and real mathematics require suitable fonts and typesetting; state specific unsupported scripts/directions or formula constructs rather than promising universal renderer support.

Store records and preferences outside the skill in the learner-controlled course space. Keep separate learners and courses separate. Do not infer weaknesses from a produced guide; record observed mistakes/questions and self-reported understanding distinctly. If persistence is unavailable provide a handoff instead of claiming permanent memory.

Renderer style overrides live in a learner/course-owned JSON file, passed with --style. Labels are configurable in the content spec; see pdf-style.md. Ordinary style changes do not modify the bundled defaults.

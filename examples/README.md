# Original university teaching example

A damped mass-spring oscillator demonstrates one connected university-level reasoning chain. Newton's force balance becomes a differential equation; an exponential trial reveals characteristic roots; conjugate roots produce real oscillations; initial displacement and velocity determine the constants. A time-response graph shows the decaying envelope, and complete practice applies the same method under changed conditions.

Every slide, problem, numerical case and figure was authored for this repository. It uses no real course, institution, lecturer, student record, classroom recording, assignment or private source. The example illustrates teaching methods; it does not establish learner mastery or performance across every discipline.

| File | Purpose |
| --- | --- |
| [source-slides.pdf](source-slides.pdf) | Three original English slides in course order. |
| [translated-slides.pdf](translated-slides.pdf) | Corresponding Chinese slides with the same objects, equations and plotted values. |
| [slide-companion.pdf](slide-companion.pdf) | Equal-scale original/translation panels, with all additional notes below. |
| [beginner-study-guide.pdf](beginner-study-guide.pdf) | Eleven connected pages with modeling, key derivations, local notation, a useful figure, a complete problem and all answers. |
| [demo-content.json](demo-content.json) | Original authored guide content and companion notes for reproducible rebuilding. |
| [demo-spec.json](demo-spec.json) | Portable input for the bundled renderer. |
| [validation.json](validation.json) | Actual page counts, authorship, export and review status. |

The guide follows all three slides. Pages 1–3 establish the model and roots; pages 4–5 connect the real solution and initial data; pages 6–7 explain the graph and exact energy balance. Page 8 contains the entire four-part authored question and the first worked part. Pages 9–10 solve the remaining parts, including the altered damping case. Page 11 checks limiting regimes and transfers the method. Routine arithmetic is concise; missing subject-specific concepts are explained where needed.

![Matched English and Chinese oscillator slides with all extra notes below](previews/comparison.png)

![Initial conditions, justified mathematical steps and envelope interpretation](previews/explanation.png)

![The complete original four-part problem and method selection](previews/practice.png)

The figure uses m = 1 kg, b = 0.4 kg/s, k = 4 N/m, initial displacement 0.1 m and initial velocity 0. It plots the exact displacement and the two envelopes over 0–10 s; curve shapes, axes, values and labels correspond across languages. The exercise resets to m = 2 kg, b = 1.2 kg/s, k = 18 N/m, displacement 0.08 m and velocity −0.03 m/s. Source and exercise parameters are kept distinct.

To rebuild, install the repository's requirements and Poppler, then run:

```bash
python scripts/build_examples.py
```

The builder stages and renders every PDF before replacing maintained artifacts. Actual page images are saved in tmp/example-qa/, outside the public bundle. Desktop previews are exported directly from actual PDF pages at 216dpi for the companion and 288 dpi for guide pages, without resampling older bitmaps. Text uses embedded Liberation Sans or Noto Sans SC Regular; mathematics uses Computer Modern vector glyphs and genuine fraction bars. Fixed UTC PDF metadata contains only the product identity. A fresh build resets visual acceptance to pending. Rendering success and matched coordinates require semantic and visual review before publication.

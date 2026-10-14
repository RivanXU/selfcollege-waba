# Original teaching example

This public example teaches constant-acceleration motion from its assumptions to
a complete assignment solution. All slides, questions, explanations and figures
were independently authored for this repository. They contain no private course
materials, classroom recordings, student answers or assessment content.

The two slide decks deliberately use **academic English and plain English** so
every public demonstration remains English. This demonstrates the same layout
contract used for translation between languages: the title, text origins,
equations, graph coordinates and other visual elements have the same geometry.
The mirror changes wording; it does not add lesson material inside the slide.
For a real course, the two decks can use any supported source and target
languages, with a font covering both languages and readable original-size text.

| File | Purpose |
| --- | --- |
| [source-slides.pdf](source-slides.pdf) | Three original slides in academic English. |
| [translated-slides.pdf](translated-slides.pdf) | The corresponding plain-English mirror with identical slide geometry. |
| [slide-companion.pdf](slide-companion.pdf) | Equal source and mirror viewports, followed by one full-width annotation band. |
| [beginner-study-guide.pdf](beginner-study-guide.pdf) | Eight spacious teaching pages: prerequisite definitions, nearby symbol meanings, justified derivation, integrated homework and transfer practice. |
| [demo-spec.json](demo-spec.json) | Reproducible companion configuration, vocabulary and bottom annotations. |
| [validation.json](validation.json) | Page counts, authorship declaration and review status. |

The guide first builds the meaning of acceleration, then derives velocity,
explains graph area and average velocity, and derives displacement. Its exact
authored homework question appears on page 6. The solution on pages 6-7 shows
how the lesson's relations answer each part and checks the result independently.
Page 8 uses new numbers to test transfer and explains the model's limits.

![Source and mirror with bottom annotations](previews/comparison.png)

![A derivation with mathematical fractions and reasons](previews/explanation.png)

![Homework calculation, graph check and interpretation](previews/practice.png)

To rebuild the files, install the repository's requirements and Poppler, then run:

```bash
python scripts/build_examples.py
```

The builder renders every PDF page and puts the complete visual review set in
`tmp/example-qa/`, which is not part of the published package. Mathematical
fractions are typeset with horizontal numerator/denominator bars. Human review
is still required before publishing a regenerated output; a successful render
does not establish teaching quality or layout fidelity by itself.

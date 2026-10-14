# Third-party components and materials

Original Selfcollege Waba files are governed by [LICENSE](LICENSE) and [NOTICE](NOTICE). Third-party components retain their own licenses.

## Python dependencies

These libraries are installed separately in the user's environment; their source code is not bundled in this package.

| Component | Purpose | License |
| --- | --- | --- |
| [ReportLab](https://www.reportlab.com/) | Text, tables, PDF layout | BSD; convenience copy at [licenses/REPORTLAB.txt](licenses/REPORTLAB.txt). |
| [pypdf](https://pypdf.readthedocs.io/) | PDF inspection and vector composition | BSD; convenience copy at [licenses/PYPDF.txt](licenses/PYPDF.txt). |
| [Matplotlib](https://matplotlib.org/) | MathText vector typesetting and example plots | [Matplotlib license](https://matplotlib.org/stable/project/license.html); retain the license included with the installed distribution. |

When installing a different distribution/version, retain and comply with that distribution's license. Mathematical vector outlines and any embedded font subsets use fonts supplied with Matplotlib. Their original notices are preserved in the [BaKoMa Computer Modern license](licenses/BAKOMA.txt), [DejaVu license](licenses/DEJAVU.txt) and [STIX license](licenses/STIX.txt).

The example builder uses [Pillow](https://pillow.readthedocs.io/) for preview images ([HPND license](https://pillow.readthedocs.io/en/stable/about.html#license)), and a separately installed [Poppler](https://poppler.freedesktop.org/) pdftoppm executable to render review images. These tools are not bundled.

## Bundled font

[assets/fonts/LiberationSans-Regular.ttf](assets/fonts/LiberationSans-Regular.ttf)
and [assets/fonts/LiberationSans-Bold.ttf](assets/fonts/LiberationSans-Bold.ttf)
are unmodified Liberation Sans fonts distributed with PDF.js. Their familiar
Helvetica/Arial-compatible metrics preserve the original English-slide style
while permitting font embedding. Retain [licenses/LIBERATION.txt](licenses/LIBERATION.txt).
Guide and feature-excerpt text uses the bundled Noto Sans SC Regular, matching
the project's original guide font and light academic hierarchy. Mathematical
outlines use Matplotlib's BaKoMa Computer Modern mathematical family, with
matching italic, Roman, symbol and extension faces. Its full notice from the
installed distribution is retained at [licenses/BAKOMA.txt](licenses/BAKOMA.txt).
No font was extracted from learner materials. The existing DejaVu/STIX notices
remain for prior assets and supported dependency fonts.

[assets/fonts/NotoSansSC-Regular.ttf](assets/fonts/NotoSansSC-Regular.ttf) is an unmodified static Noto Sans SC Regular font obtained from [Google Fonts](https://fonts.google.com/noto/specimen/Noto+Sans+SC). Its copyright and SIL Open Font License are preserved at [assets/fonts/OFL.txt](assets/fonts/OFL.txt). The font is independently licensed and is not subject to the project's PolyForm license.

You may select another font you are authorized to embed. Different scripts and complex text shaping require appropriate fonts and rendering tools.

## Educational material

Public examples are original material authored for this project; they are not copied from a real course or examination. Learner-supplied slides, textbooks, transcripts, assignments, and images retain their original rights. Generating a PDF does not transfer those rights to the author or relicense a learner's independently authored content.

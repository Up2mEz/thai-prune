# Short paper: IEEE-format sources (English and Thai)

| | English | Thai |
|---|---|---|
| Source | `en/main_en.tex` | `th/main_th.tex` |
| PDF | `en/main_en.pdf` | `th/main_th.pdf` |
| Template | `IEEEtran` (conference, two columns); Times New Roman | Single column, Angsana New (the Thai example's format); headings kept in English |
| Figures | `../figures/fig_*_en.pdf` (3.5 in wide, 8 pt) | `../figures/fig_*_th.pdf` (4.6 in wide, 10 pt) |

Build, from `en/` or `th/` (XeLaTeX is required for the Thai font and shaping):

```bash
xelatex main_en && bibtex main_en && xelatex main_en && xelatex main_en
```

Use `main_th` in `th/`. MiKTeX may ask to install a package the first time; the
only extra package the English version needs is `IEEEtran`.

Figures come from `scripts/paper_make_figures.py` and `figure_data.json`
(every number cites its results document). They need matplotlib 3.11 or newer,
whose text layout shapes Thai stacked vowels and tone marks correctly:

```bash
uv run --with matplotlib python scripts/paper_make_figures.py
```

Red `[...]` marks in the PDFs wait for the collaborator's runs (work split
W1--W4). Author names are copied from the earlier draft; confirm them.

## Diagram made in Paper (design tool)

`../figures/fig_stages_en.pdf` (and `.png`) is the conceptual diagram "Where a
Thai mark can be lost", drawn in Paper Desktop (file "Neat cloud") at 1400 px
wide so that scaling to one IEEE column (3.5 in) gives about 8 pt text. The
exported PDF is vector with embedded Times New Roman and selectable text. Its
numbers are typed by hand from `figure_data.json`; it is not yet included in
`main_en.tex` or `main_th.tex`.

## Version 2: the format of `docs/paper/Example/`

`v2/en/main_en.tex` and `v2/th/main_th.tex` follow the two example PDFs: IEEE
conference format with italic title, per-author blocks and a copyright line
(English, US Letter), and an A4 Thai page with a single-column title page,
abstract, keywords and footnotes followed by two justified columns (Thai).
Abstract, keywords and body are shared files in each folder (`abstract_*.tex`,
`keywords_*.tex`, `body_*.tex`). Thai figures for this version are
`fig_*_th2.pdf` (3.1 in wide). Thai font: Browallia New (installed with Windows),
used because the example's font is not installed; swap it in `main_th.tex` if
you have the original.

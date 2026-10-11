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

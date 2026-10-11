"""Draw the short paper's figures from docs/paper/figure_data.json.

Run: uv run --with matplotlib python scripts/paper_make_figures.py
Writes docs/paper/figures/fig_<name>_<lang>.pdf for lang in {en, th}.

Conventions (IEEE Author Center graphics guidance, checked 2026-10-11):
- width = one printed column (3.5 in) for English; the Thai paper is single
  column, so its figures are drawn at 4.6 in. Text is 8 pt (English) and 10 pt
  (Thai) at that final size, one family per language, vector PDF, TrueType
  fonts embedded (pdf.fonttype 42).
- No titles inside figures (captions carry them); panels are lettered (a)/(b)
  (Thai: ก/ข); units in parentheses; direct labels instead of legends;
  bars start at zero; Okabe-Ito colours plus hatching as secondary encoding.
- Thai text relies on matplotlib >= 3.11 (HarfBuzz/Raqm text layout); the Thai
  figures were checked by eye for stacked vowels and tone marks.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs/paper/figure_data.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs/paper/figures"
THAI_FONT = ROOT / "assets/fonts/noto/NotoSansThai-Regular.ttf"
INK, MUTED, GRID = "#1F2328", "#6B7280", "#E6E8EB"
BLUE, GREY, ORANGE, SKY, PINK = "#0072B2", "#9AA0A6", "#D55E00", "#F2A97A", "#CC79A7"

STYLE = {"en": {"width": 3.5, "font": 8.0, "family": "Times New Roman"},
         "th": {"width": 4.6, "font": 10.0, "family": ["Arial", "Noto Sans Thai"]},
         "th2": {"width": 3.1, "font": 8.5, "family": ["Arial", "Noto Sans Thai"]}}  # th2: two-column Thai paper
TEXT = {
    "en": {
        "panel": ("(a)", "(b)"),
        "causes": ["read in another order", "whole line absent", "span missing", "misread"],
        "causes_x": "Share of all reference marks (%)",
        "methods": ["Repetition penalty 1.1", "n-gram blocking", "Stop at loop"],
        "decoders_x": "Change in mark F1 vs. greedy (points)",
        "all": "all pages", "free": "loop-free pages",
        "gain_x": "Gain from the image (points)",
        "lam_x": "Prior weight λ", "lam_y": "Tone accuracy (%)",
        "f1_x": "Mark F1 (%)", "full": "Full-page", "text": "Text recognition",
    },
    "th": {
        "panel": ("(ก)", "(ข)"),
        "causes": ["อ่านในลำดับอื่น", "หายทั้งบรรทัด", "ขาดเป็นช่วง", "อ่านผิดตัว"],
        "causes_x": "สัดส่วนของ mark ในเฉลยทั้งหมด (%)",
        "methods": ["Repetition penalty 1.1", "n-gram blocking", "หยุดเมื่อวนซ้ำ"],
        "decoders_x": "การเปลี่ยนของ mark F1 เทียบ greedy (จุด)",
        "all": "ทุกหน้า", "free": "หน้าที่ไม่วนซ้ำ",
        "gain_x": "ภาพช่วยเพิ่มความแม่นยำ (จุด)",
        "lam_x": "น้ำหนักความรู้ภาษาที่หัก λ", "lam_y": "ความแม่นยำ (%)",
        "f1_x": "Mark F1 (%)", "full": "อ่านทั้งหน้า", "text": "อ่านข้อความสั้น",
    },
}
TEXT["th2"] = TEXT["th"]
HATCH = ["", "//", "..", "xx"]


def _setup(lang: str):
    s = STYLE[lang]
    if lang.startswith("th"):
        fm.fontManager.addfont(str(THAI_FONT))
    plt.rcParams.update({
        "font.family": s["family"], "font.size": s["font"], "axes.labelsize": s["font"],
        "xtick.labelsize": s["font"], "ytick.labelsize": s["font"],
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
        "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42, "hatch.linewidth": 0.5, "mathtext.fontset": "dejavusans",
    })
    return s


def _save(fig, name: str, lang: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"fig_{name}_{lang}.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def causes(lang: str) -> None:
    s, t = _setup(lang), TEXT[lang]
    d = DATA["attribution_typhoon_fullpage_pct_of_all_marks"]
    keys = ["other_order", "whole_line_absent", "span_missing", "misread"]
    colors = [GREY, ORANGE, SKY, PINK]
    fig, ax = plt.subplots(figsize=(s["width"], 1.45 if lang == "en" else 1.8))
    for row, prompt in enumerate(("BQ", "TC")):
        left = 0.0
        for i, key in enumerate(keys):
            v = d[prompt][key]
            ax.barh(row, v, left=left, color=colors[i], hatch=HATCH[i], edgecolor="white",
                    linewidth=0.8, height=0.58)
            ax.text(left + v / 2, row, f"{v:.1f}", ha="center", va="center", color=INK,
                    fontsize=s["font"] - 0.5, bbox={"fc": "white", "ec": "none", "pad": 0.6, "alpha": 0.75})
            if row == 0:  # direct labels above the first bar, staggered, same order for both bars
                lift = 4 + 11 * (i % 2)
                ax.annotate(t["causes"][i], (left + v / 2, row - 0.29), xytext=(0, lift),
                            textcoords="offset points", ha="center", va="bottom",
                            fontsize=s["font"] - 1, color=INK,
                            arrowprops={"arrowstyle": "-", "lw": 0.5, "color": MUTED,
                                        "shrinkA": 0, "shrinkB": 0})
            left += v
    ax.set_yticks([0, 1], ["BQ", "TC"])
    ax.set_ylim(1.45, -1.25)
    ax.set_xlim(0, 7.4)
    ax.set_xlabel(t["causes_x"])
    ax.xaxis.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    _save(fig, "causes", lang)


def models(lang: str) -> None:
    s, t = _setup(lang), TEXT[lang]
    d = DATA["five_models_mark_f1"]
    fig, axes = plt.subplots(1, 2, figsize=(s["width"], 1.7 if lang == "en" else 2.1), sharey=True)
    colors = [BLUE] + [GREY] * 4
    for ax, key, panel in zip(axes, ("full_page", "text_recognition"), t["panel"]):
        vals = d[key]
        ax.barh(range(len(vals)), vals, color=colors, height=0.62)
        for i, v in enumerate(vals):
            ax.text(v + 1.5, i, f"{v:.1f}", va="center", fontsize=s["font"] - 0.5)
        ax.set_xlim(0, 118)
        ax.set_xlabel(t["f1_x"])
        ax.text(0.0, 1.04, panel, transform=ax.transAxes, fontsize=s["font"], fontweight="bold", va="bottom")
        ax.xaxis.grid(True, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)
    axes[0].set_yticks(range(len(d["models"])), d["models"])
    axes[0].invert_yaxis()
    fig.subplots_adjust(wspace=0.08)
    _save(fig, "models", lang)


def decoders(lang: str) -> None:
    s, t = _setup(lang), TEXT[lang]
    d = DATA["decoders_typhoon_fullpage_bq_delta_f1"]
    fig, ax = plt.subplots(figsize=(s["width"], 1.55 if lang == "en" else 1.9))
    h = 0.36
    for i, (allp, free, ci) in enumerate(zip(d["all_pages"], d["loop_free_pages"], d["all_pages_ci95"])):
        ax.barh(i - h / 2, allp, height=h, color=BLUE, xerr=[[allp - ci[0]], [ci[1] - allp]],
                error_kw={"elinewidth": 0.7, "capsize": 1.8, "capthick": 0.7, "ecolor": INK})
        ax.barh(i + h / 2, free, height=h, color=ORANGE, hatch="//", edgecolor="white", linewidth=0)
        ax.text(min(free, 0) - 0.08 if free < 0 else 0.08, i + h / 2, f"{free:+.2f}", va="center",
                ha="right" if free < 0 else "left", fontsize=s["font"] - 0.5)
        ax.text(ci[1] + 0.1, i - h / 2, f"{allp:+.2f}", va="center", fontsize=s["font"] - 0.5)
    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set_yticks(range(3), t["methods"])
    ax.set_ylim(2.65, -0.65)
    ax.set_xlim(-3.2, 6.2)
    ax.set_xlabel(t["decoders_x"])
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=BLUE, label=t["all"] + (" (95% CI)" if lang == "en" else " (CI 95%)")),
                       Patch(fc=ORANGE, hatch="//", ec="white", label=t["free"])],
              loc="upper center", bbox_to_anchor=(0.45, -0.32), ncol=2, frameon=False,
              fontsize=s["font"] - 0.5, handlelength=1.4, columnspacing=1.2)
    ax.xaxis.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    _save(fig, "decoders", lang)


def prior(lang: str) -> None:
    s, t = _setup(lang), TEXT[lang]
    d = DATA["tone_accuracy_typhoon_fullpage"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(s["width"], 1.5 if lang == "en" else 1.9),
                               gridspec_kw={"width_ratios": [1, 1.05], "wspace": 0.7})
    gains = [d["typhoon"]["with_image"] - d["typhoon"]["without_image"],
             d["base"]["with_image"] - d["base"]["without_image"]]
    names, colors = ["Typhoon", "Qwen3-VL-2B"], [BLUE, GREY]
    a.barh([0, 1], gains, color=colors, height=0.5)
    for y, g in enumerate(gains):
        a.text(g + (0.06 if g >= 0 else -0.06), y, f"{g:+.1f}", va="center",
               ha="left" if g >= 0 else "right", fontsize=s["font"] - 0.5)
    a.axvline(0, color=INK, linewidth=0.8)
    a.set_yticks([0, 1], names)
    a.set_ylim(1.6, -0.6)
    a.set_xlim(-1.9, 1.9)
    a.set_xlabel(t["gain_x"])
    a.xaxis.grid(True, color=GRID, linewidth=0.5)
    a.set_axisbelow(True)
    a.text(0.0, 1.03, t["panel"][0], transform=a.transAxes, fontsize=s["font"], fontweight="bold", va="bottom")
    lam = d["typhoon_contrastive_lambda"]
    b.plot(lam["lambda"], lam["accuracy"], "-o", color=BLUE, markersize=4, linewidth=1.2)
    for x, y in zip(lam["lambda"], lam["accuracy"]):
        b.annotate(f"{y:.1f}", (x, y), xytext=(0, 5), textcoords="offset points", ha="center",
                   fontsize=s["font"] - 0.5)
    b.set_ylim(0, 118)
    b.set_xlim(-0.1, 1.1)
    b.set_xticks([0, 0.5, 1])
    b.set_xlabel(t["lam_x"])
    b.set_ylabel(t["lam_y"])
    b.text(0.0, 1.03, t["panel"][1], transform=b.transAxes, fontsize=s["font"], fontweight="bold", va="bottom")
    b.yaxis.grid(True, color=GRID, linewidth=0.5)
    b.set_axisbelow(True)
    _save(fig, "prior", lang)


if __name__ == "__main__":
    for language in ("en", "th", "th2"):
        causes(language)
        models(language)
        decoders(language)
        prior(language)
    print("wrote", sorted(p.name for p in OUT.glob("fig_*_*.pdf")))

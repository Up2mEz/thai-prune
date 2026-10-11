"""Draw the short paper's figures from docs/paper/figure_data.json.

Run: uv run --with matplotlib python scripts/paper_make_figures.py
Writes PDF figures to docs/paper/figures/. Labels are English so that no Thai
shaping is needed in the figures; every figure is labelled directly.
Palette: Okabe-Ito entries, checked with the dataviz validator.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs/paper/figure_data.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs/paper/figures"
INK, MUTED, GRID = "#1F2328", "#6B7280", "#E6E8EB"
BLUE, GREY, ORANGE, SKY, PINK, GREEN = "#0072B2", "#9AA0A6", "#D55E00", "#F2A97A", "#CC79A7", "#009E73"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
})


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def causes() -> None:
    d = DATA["attribution_typhoon_fullpage_pct_of_all_marks"]
    parts = [("other_order", "read in another order", GREY), ("whole_line_absent", "whole line absent", ORANGE),
             ("span_missing", "span missing", SKY), ("misread", "misread", PINK)]
    fig, ax = plt.subplots(figsize=(3.3, 1.7))
    for row, prompt in enumerate(("BQ", "TC")):
        left = 0.0
        for key, label, color in parts:
            v = d[prompt][key]
            ax.barh(row, v, left=left, color=color, edgecolor="white", linewidth=1.2, height=0.55)
            ax.text(left + v / 2, row, f"{v:.1f}", ha="center", va="center", fontsize=7, color=INK)
            left += v
    for i, (_, label, color) in enumerate(parts):
        ax.barh(-9, 0, color=color, label=label)
    ax.set_yticks([0, 1], ["BQ", "TC"])
    ax.set_ylim(1.5, -0.7)
    ax.set_xlabel("% of all reference marks (Typhoon, full-page)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, frameon=False, fontsize=7)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    _save(fig, "fig_causes")


def models() -> None:
    d = DATA["five_models_mark_f1"]
    fig, axes = plt.subplots(1, 2, figsize=(3.3, 1.9), sharey=True)
    colors = [BLUE] + [GREY] * 4
    for ax, key, title in zip(axes, ("full_page", "text_recognition"), ("Full-page", "Text recognition")):
        vals = d[key]
        ax.barh(range(len(vals)), vals, color=colors, height=0.62)
        for i, v in enumerate(vals):
            ax.text(v + 1.5, i, f"{v:.1f}", va="center", fontsize=7)
        ax.set_title(title, fontsize=8, color=INK)
        ax.set_xlim(0, 112)
        ax.set_xlabel("mark F1")
        ax.xaxis.grid(True, color=GRID)
        ax.set_axisbelow(True)
    axes[0].set_yticks(range(len(d["models"])), d["models"], fontsize=6.5)
    axes[0].invert_yaxis()
    _save(fig, "fig_models")


def decoders() -> None:
    d = DATA["decoders_typhoon_fullpage_bq_delta_f1"]
    fig, ax = plt.subplots(figsize=(3.3, 1.8))
    h = 0.34
    for i, (name, allp, free) in enumerate(zip(d["methods"], d["all_pages"], d["loop_free_pages"])):
        ax.barh(i - h / 2, allp, height=h, color=BLUE, label="all pages" if i == 0 else None)
        ax.barh(i + h / 2, free, height=h, color=ORANGE, label="loop-free pages only" if i == 0 else None)
        for dy, v in ((-h / 2, allp), (h / 2, free)):
            ax.text(v + (0.06 if v >= 0 else -0.06), i + dy, f"{v:+.2f}", va="center",
                    ha="left" if v >= 0 else "right", fontsize=7)
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_yticks(range(3), d["methods"])
    ax.set_ylim(2.6, -0.6)
    ax.set_xlim(-1.9, 1.5)
    ax.set_xlabel("change in mark F1 vs. greedy (points)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2, frameon=False, fontsize=7)
    _save(fig, "fig_decoders")


def prior() -> None:
    d = DATA["tone_accuracy_typhoon_fullpage"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(3.3, 1.8), gridspec_kw={"width_ratios": [1, 1.1]})
    for y, name, color in ((0, "Typhoon", BLUE), (1, "Qwen3-VL-2B", GREY)):
        key = "typhoon" if y == 0 else "base"
        w, wo = d[key]["with_image"], d[key]["without_image"]
        a.plot([wo, w], [y, y], color=color, linewidth=1.2)
        a.plot(w, y, "o", color=color, markersize=6)
        a.plot(wo, y, "o", color="white", markeredgecolor=color, markersize=6)
        a.text((w + wo) / 2, y - 0.28, name, ha="center", va="bottom", fontsize=7)
    a.set_yticks([])
    a.spines["left"].set_visible(False)
    a.set_ylim(1.6, -0.8)
    a.set_xlim(97.6, 100.4)
    a.set_xlabel("tone accuracy, %")
    a.set_title("filled: with image\nhollow: without", fontsize=6.5, color=MUTED)
    lam = d["typhoon_contrastive_lambda"]
    b.plot(lam["lambda"], lam["accuracy"], "-o", color=BLUE, markersize=4, linewidth=1.2)
    for x, y in zip(lam["lambda"], lam["accuracy"]):
        b.text(x, y + 6, f"{y:.1f}", ha="center", fontsize=7)
    b.set_ylim(0, 118)
    b.set_xlabel(r"$\lambda$ (prior subtracted)")
    b.set_title("Typhoon, contrastive", fontsize=6.5, color=MUTED)
    b.yaxis.grid(True, color=GRID)
    b.set_axisbelow(True)
    _save(fig, "fig_prior")


if __name__ == "__main__":
    causes()
    models()
    decoders()
    prior()
    print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))

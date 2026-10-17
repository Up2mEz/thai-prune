"""Draw the slide deck's Plotly charts from docs/paper/figure_data.json.

Run:
    uv run --with plotly --with kaleido python scripts/slides_make_charts.py
Writes docs/paper/slides/charts/*.png (scale 2) and, with --svg, the same as SVG.

Spec: docs/presentdesign.md ("วิธีทำกราฟ") and docs/paper/SLIDES_CONTENT.md
("ภาพที่ต้องทำและข้อมูลจากไหน"). Plotly + Kaleido (Chrome renders the text, so stacked
Thai vowels and tone marks are placed correctly), template simple_white, Okabe-Ito colours,
no title inside the chart, numbers on the bars, no grid, direct labels instead of a legend.

Size: 1 px = 0.6 pt on a 13.33 in wide slide (1600 px). So 30 px is 18 pt (numbers),
24 px is 14 pt (labels) and nothing is below 20 px (12 pt).

Font: the stack starts with Noto Sans Thai (the project's choice). It is used if it is installed
on the machine; otherwise Chrome falls back to Leelawadee UI or Tahoma, which also shape Thai
correctly. The Noto bold weights are not in the repository, so bold is the fallback family's.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs/paper/figure_data.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs/paper/slides/charts"

FONT = "Noto Sans Thai, Leelawadee UI, Tahoma, sans-serif"
INK, MUTED, ZERO = "#1F2328", "#6B7280", "#6B7280"
BLUE, GREY, GREEN, RED = "#0072B2", "#9AA0A6", "#009E73", "#D55E00"
SOFT_RED, PINK, LIGHT_GREY, AMBER = "#F2A97A", "#CC79A7", "#C9CDD2", "#E69F00"
MINUS = "−"

NUM = 30   # numbers on bars (18 pt)
LAB = 24   # labels and axis titles (14 pt)
TICK = 22  # tick labels (13 pt)


def signed(v: float, digits: int = 1) -> str:
    text = f"{v:+.{digits}f}"
    return text.replace("-", MINUS)


def base_layout(fig: go.Figure, width: int, height: int) -> None:
    fig.update_layout(
        template="simple_white", width=width, height=height,
        font={"family": FONT, "size": LAB, "color": INK},
        paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
        margin={"l": 20, "r": 40, "t": 30, "b": 20},
    )


def rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def save(fig: go.Figure, name: str, svg: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.write_image(OUT / f"{name}.png", scale=2)
    if svg:
        fig.write_image(OUT / f"{name}.svg")
    print("wrote", name)


# ---- slide 5: where marks are lost (stacked horizontal bars) -------------------------------
def s05_causes(svg: bool) -> None:
    d = DATA["attribution_cross_model_fullpage_stopped_pct_of_all_marks"]
    f1 = DATA["five_models_mark_f1"]["full_page"]
    labels = [f"{m} ({s:.1f})" for m, s in zip(d["models"], f1)]
    parts = [  # key, Thai name, colour, label colour
        ("other_order", "คนละลำดับ (ไม่ใช่ความผิดจริง)", LIGHT_GREY, INK),
        ("whole_line_absent", "ทั้งบรรทัดไม่ปรากฏใน output", RED, "white"),
        ("span_missing", "ขาดเป็นช่วง", SOFT_RED, INK),
        ("misread", "อ่านผิดตัว", PINK, INK),
    ]
    fig = go.Figure()
    for key, name, colour, label_colour in parts:
        vals = d[key]
        fig.add_bar(
            y=labels, x=vals, orientation="h", marker={"color": colour, "line": {"color": "white", "width": 2}},
            text=[f"{v:.1f}" if v >= 4.5 else "" for v in vals], textposition="inside", insidetextanchor="middle",
            textfont={"size": NUM, "color": label_colour}, name=name,
        )
    totals = [sum(d[k][i] for k in ("whole_line_absent", "span_missing", "misread")) for i in range(len(labels))]
    for i, total in enumerate(totals):
        right = sum(d[k][i] for k, *_ in parts)
        fig.add_annotation(x=right + 0.8, y=labels[i], text=f"<b>{total:.1f}</b>", showarrow=False,
                           xanchor="left", font={"size": NUM, "color": INK})
    fig.update_layout(barmode="stack", bargap=0.35)
    fig.update_xaxes(range=[0, 68], title_text="สัดส่วนของ mark ในเฉลยทั้งหมด (%) · ตัวเลขท้ายแท่ง = ไม่นับสีเทา",
                     showgrid=False, tickfont={"size": TICK}, title_font={"size": LAB})
    fig.update_yaxes(autorange="reversed", tickfont={"size": LAB}, showline=False, ticks="")
    x0 = 0.0
    for _, name, colour, _ in parts:  # direct labels: coloured names along the top
        fig.add_annotation(xref="paper", yref="paper", x=x0, y=1.07, text=f"<b>■</b> {name}",
                           showarrow=False, xanchor="left", font={"size": TICK, "color": colour if colour != LIGHT_GREY else MUTED})
        x0 += {"คนละลำดับ (ไม่ใช่ความผิดจริง)": 0.31, "ทั้งบรรทัดไม่ปรากฏใน output": 0.31, "ขาดเป็นช่วง": 0.17}.get(name, 0)
    base_layout(fig, 1600, 900)
    fig.update_layout(margin={"l": 20, "r": 40, "t": 80, "b": 20})
    save(fig, "s05_causes", svg)


# ---- slide 6 left: image gain in the forced-choice test ------------------------------------
def s06a_image_gain(svg: bool) -> None:
    d = DATA["image_gain_fullpage_tone_calibration"]
    colours = [BLUE, BLUE, GREY, GREY]
    fig = go.Figure(go.Bar(
        y=d["models"], x=d["gain"], orientation="h", marker={"color": colours},
        text=[signed(v) for v in d["gain"]], textposition="outside", textfont={"size": NUM, "color": INK},
        cliponaxis=False,
    ))
    fig.add_vline(x=0, line={"color": ZERO, "width": 2})
    fig.update_xaxes(range=[-1.5, 1.6], title_text="ภาพช่วยเพิ่มความแม่นยำของวรรณยุกต์ (จุด)", showgrid=False,
                     tickfont={"size": TICK}, title_font={"size": LAB}, zeroline=False)
    fig.update_yaxes(autorange="reversed", tickfont={"size": LAB}, showline=False, ticks="")
    fig.update_layout(bargap=0.4)
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.08, showarrow=False, xanchor="left",
                       text=f"<span style='color:{BLUE}'>■</span> Thai fine-tune   <span style='color:{GREY}'>■</span> โมเดลทั่วไป",
                       font={"size": TICK, "color": MUTED})
    base_layout(fig, 800, 900)
    fig.update_layout(margin={"l": 20, "r": 70, "t": 80, "b": 20})
    save(fig, "s06a_image_gain", svg)


# ---- slide 6 right: written by the model vs the forced-choice test --------------------------
def s06b_generate_vs_test(svg: bool) -> None:
    d = DATA["tone_accuracy_generation_vs_test_fullpage_correct_base"]
    models = d["models"]
    colours = [BLUE, GREY]
    fig = go.Figure()
    for j, (series, label, alpha) in enumerate((("generation", "เขียนเอง", 1.0), ("test", "การทดสอบ", 0.4))):
        fig.add_bar(
            x=models, y=d[series], name=label, width=0.36,
            marker={"color": [rgba(c, alpha) for c in colours], "line": {"color": colours, "width": 3 if alpha < 1 else 0}},
            text=[f"{v:.1f}" for v in d[series]], textposition="outside", textfont={"size": NUM, "color": INK},
            cliponaxis=False, offsetgroup=j,
        )
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_yaxes(range=[85, 101.5], title_text="ความแม่นยำของวรรณยุกต์ (%) · แกนเริ่มที่ 85%", showgrid=False,
                     tickfont={"size": TICK}, title_font={"size": LAB}, dtick=5)
    fig.update_xaxes(tickfont={"size": LAB}, showline=True)
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.08, showarrow=False, xanchor="left",
                       text="แท่งเต็ม = เขียนเอง · แท่งโปร่ง = การทดสอบ", font={"size": TICK, "color": MUTED})
    base_layout(fig, 800, 900)
    fig.update_layout(margin={"l": 20, "r": 30, "t": 80, "b": 20})
    save(fig, "s06b_generate_vs_test", svg)


# ---- slide 7: three ways to handle a loop (Typhoon, calibration) ---------------------------
def s07_decoders(svg: bool) -> None:
    d = DATA["decoders_typhoon_fullpage_bq_delta_f1"]
    names = ["repetition penalty 1.1", "ห้ามซ้ำ n-gram", "หยุดเมื่อวนซ้ำ"]
    allp, free, ci = d["all_pages"], d["loop_free_pages"], d["all_pages_ci95"]
    pos = lambda v: GREEN if v > 0 else (RED if v < 0 else GREY)  # noqa: E731
    y_all = [i - 0.2 for i in range(3)]
    y_free = [i + 0.2 for i in range(3)]
    fig = go.Figure()
    fig.add_bar(
        y=y_all, x=allp, orientation="h", width=0.34, marker={"color": [pos(v) for v in allp]},
        error_x={"type": "data", "symmetric": False, "array": [c[1] - v for c, v in zip(ci, allp)],
                 "arrayminus": [v - c[0] for c, v in zip(ci, allp)], "color": INK, "thickness": 2.5, "width": 8},
    )
    fig.add_bar(
        y=y_free, x=free, orientation="h", width=0.34,
        marker={"color": [rgba(pos(v), 0.4) for v in free], "line": {"color": [pos(v) for v in free], "width": 3}},
    )
    for y, v, c in zip(y_all, allp, ci):  # value beyond the interval, so the line never crosses it
        x, anchor = (c[1] + 0.15, "left") if v >= 0 else (c[0] - 0.15, "right")
        fig.add_annotation(x=x, y=y, text=f"<b>{signed(v, 2)}</b>", showarrow=False, xanchor=anchor,
                           font={"size": NUM, "color": INK})
    for y, v in zip(y_free, free):
        x, anchor = (v + 0.15, "left") if v > 0 else (min(v, 0) - 0.15, "right")
        fig.add_annotation(x=x, y=y, text=signed(v, 2) if v else "0.00", showarrow=False, xanchor=anchor,
                           font={"size": NUM, "color": INK})
    fig.add_vline(x=0, line={"color": ZERO, "width": 2})
    fig.update_layout(bargap=0.3)
    fig.update_xaxes(range=[-4.2, 7.6], title_text="การเปลี่ยนของคะแนน mark เทียบ greedy (จุด)", showgrid=False,
                     tickfont={"size": TICK}, title_font={"size": LAB}, zeroline=False)
    fig.update_yaxes(range=[2.6, -0.6], tickvals=[0, 1, 2], ticktext=names, tickfont={"size": LAB}, showline=False, ticks="")
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.08, showarrow=False, xanchor="left",
                       text="แท่งเต็ม = ทุกหน้า (ช่วงความเชื่อมั่น 95%) · แท่งโปร่ง = เฉพาะหน้าที่ไม่วนซ้ำ",
                       font={"size": TICK, "color": MUTED})
    base_layout(fig, 1100, 900)
    fig.update_layout(margin={"l": 20, "r": 60, "t": 80, "b": 20})
    save(fig, "s07_decoders", svg)


# ---- slide 8: eight models on the locked split, greedy vs stop ------------------------------
def s08_locked(svg: bool) -> None:
    d = DATA["locked_eight_models_mark_f1"]
    models = d["models"]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                        subplot_titles=("อ่านทั้งหน้า (128 ข้อ)", "อ่านข้อความสั้น (224 ข้อ)"))
    for col, task in ((1, "full_page"), (2, "text_recognition")):
        for j, (series, name, colour) in enumerate(((f"{task}_greedy", "greedy", GREY), (f"{task}_stop", "+ หยุด", GREEN))):
            fig.add_bar(
                y=models, x=d[series], orientation="h", name=name, marker={"color": colour}, width=0.36, offsetgroup=j,
                text=[f"{v:.1f}" for v in d[series]], textposition="outside", textfont={"size": 24, "color": INK},
                cliponaxis=False, row=1, col=col,
            )
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_xaxes(range=[0, 118], showgrid=False, tickvals=[0, 25, 50, 75, 100], tickfont={"size": TICK},
                     title_text="คะแนน mark (%)", title_font={"size": LAB})
    fig.update_yaxes(autorange="reversed", tickfont={"size": LAB}, showline=False, ticks="")
    fig.update_annotations(font={"size": LAB, "color": INK})
    fig.add_annotation(xref="paper", yref="paper", x=0, y=-0.17, showarrow=False, xanchor="left",
                       text=f"<span style='color:{GREY}'>■</span> greedy   <span style='color:{GREEN}'>■</span> + หยุดเมื่อวนซ้ำ",
                       font={"size": TICK, "color": MUTED})
    fig.add_annotation(xref="paper", yref="paper", x=1, y=-0.17, showarrow=False, xanchor="right",
                       text="<b>Pathumma อ่านทั้งหน้า: ไม่ผ่านตามเกณฑ์ที่ลงทะเบียน</b>", font={"size": TICK, "color": RED})
    base_layout(fig, 1250, 900)
    fig.update_layout(margin={"l": 20, "r": 40, "t": 70, "b": 130})
    save(fig, "s08_locked", svg)


# ---- backup B2: R1 ratio with intervals ------------------------------------------------------
def b02_r1_forest(svg: bool) -> None:
    d = DATA["locked_r1_ratio_fullpage"]
    models, ratio, lo, hi = d["models"], d["ratio"], d["ci_low"], d["ci_high"]
    fig = go.Figure(go.Scatter(
        y=models, x=ratio, mode="markers+text", marker={"color": BLUE, "size": 18},
        error_x={"type": "data", "symmetric": False, "array": [h - r for h, r in zip(hi, ratio)],
                 "arrayminus": [r - low for r, low in zip(ratio, lo)], "color": BLUE, "thickness": 3.5, "width": 10},
        text=[f"{r:.1f}" for r in ratio], textposition="top center", textfont={"size": NUM, "color": INK},
    ))
    fig.add_vline(x=3, line={"color": RED, "width": 3, "dash": "dash"})
    fig.add_annotation(x=3, y=1.0, yref="paper", text="เกณฑ์ = 3", showarrow=False, xanchor="left", yanchor="bottom",
                       font={"size": LAB, "color": RED})
    fig.update_xaxes(range=[0, 34], title_text="ข้อความที่ไม่ปรากฏ ÷ mark ที่อ่านผิด (เท่า) · ช่วงความเชื่อมั่น 95%",
                     showgrid=False, tickfont={"size": TICK}, title_font={"size": LAB})
    fig.update_yaxes(autorange="reversed", tickfont={"size": LAB}, showline=False, ticks="")
    base_layout(fig, 1600, 900)
    fig.update_layout(margin={"l": 20, "r": 40, "t": 60, "b": 20})
    save(fig, "b02_r1_forest", svg)


# ---- backup B3: calibration mark F1, six models -----------------------------------------------
def b03_calibration_f1(svg: bool) -> None:
    d = DATA["five_models_mark_f1"]
    models = d["models"]
    colours = [BLUE, BLUE, GREY, GREY, GREY, GREY]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=("อ่านทั้งหน้า (69 ข้อ)", "อ่านข้อความสั้น (109 ข้อ)"))
    for col, key in ((1, "full_page"), (2, "text_recognition")):
        fig.add_bar(y=models, x=d[key], orientation="h", marker={"color": colours}, width=0.6,
                    text=[f"{v:.1f}" for v in d[key]], textposition="outside", textfont={"size": NUM, "color": INK},
                    cliponaxis=False, row=1, col=col)
    fig.update_xaxes(range=[0, 118], showgrid=False, tickvals=[0, 25, 50, 75, 100], tickfont={"size": TICK},
                     title_text="คะแนน mark (%)", title_font={"size": LAB})
    fig.update_yaxes(autorange="reversed", tickfont={"size": LAB}, showline=False, ticks="")
    fig.update_annotations(font={"size": LAB, "color": INK})
    fig.add_annotation(xref="paper", yref="paper", x=0, y=-0.17, showarrow=False, xanchor="left",
                       text=f"<span style='color:{BLUE}'>■</span> Thai fine-tune   <span style='color:{GREY}'>■</span> โมเดลอื่น (calibration)",
                       font={"size": TICK, "color": MUTED})
    base_layout(fig, 1600, 900)
    fig.update_layout(margin={"l": 20, "r": 40, "t": 70, "b": 130})
    save(fig, "b03_calibration_f1", svg)


CHARTS = {
    "s05": s05_causes, "s06a": s06a_image_gain, "s06b": s06b_generate_vs_test, "s07": s07_decoders,
    "s08": s08_locked, "b02": b02_r1_forest, "b03": b03_calibration_f1,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", choices=sorted(CHARTS), help="draw only these charts")
    parser.add_argument("--svg", action="store_true", help="also write SVG")
    args = parser.parse_args()
    for key in args.only or CHARTS:
        CHARTS[key](args.svg)


if __name__ == "__main__":
    main()

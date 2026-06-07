#!/usr/bin/env python3
"""Convert fig01_architecture_en.py (matplotlib) → .drawio (diagrams.net).

Coordinate mapping:
  - Canvas: 1056 × 768 px  (= 11 × 8 inches @ 96 DPI)
  - drawio x = data_x × 48
  - drawio y = (16 − data_y) × 48   (matplotlib y-up → drawio y-down)
  - 1 data unit = 48 px
"""

import os
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

# ── helpers ─────────────────────────────────────────────────────────────

def d2x(dx):
    """Map matplotlib data-x (0-22) → drawio x (px)."""
    return round(dx * 48, 1)

def d2y(dy):
    """Map matplotlib data-y (0-16, upward) → drawio y (px, downward)."""
    return round((16 - dy) * 48, 1)

def d2w(dw):
    return round(dw * 48, 1)

def d2h(dh):
    return round(dh * 48, 1)

_COUNTER = [0]  # mutable counter for unique cell ids

def nid():
    _COUNTER[0] += 1
    return str(_COUNTER[0])


def cell_style(**kw):
    """Build drawio style string from keyword args."""
    return ";".join(f"{k}={v}" for k, v in kw.items() if v is not None)


# ── atomic element builders ─────────────────────────────────────────────

def rect_cell(x, y, w, h, label, *,
              fill=None, stroke="#000000", stroke_width=1,
              rounded=1, arc_size=8, font_size=10, font_color="#000000",
              bold=0, italic=0, align="center", valign="middle",
              dashed=0, html=1):
    cid = nid()
    style = cell_style(
        rounded=rounded, arcSize=arc_size,
        whiteSpace="wrap", html=html,
        fillColor=fill, strokeColor=stroke, strokeWidth=stroke_width,
        fontSize=font_size, fontColor=font_color,
        fontStyle=(1 if bold else 0) + (2 if italic else 0),
        horizontal=1, align=align, verticalAlign=valign,
        dashed=dashed, dashPattern="5 3" if dashed else None,
    )
    geom = f'<mxGeometry x="{d2x(x)}" y="{d2y(y+h)}" width="{d2w(w)}" height="{d2h(h)}" as="geometry"/>'
    cell = f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">{geom}</mxCell>'
    return cell, cid


def rect_abs(x, y, w, h, label, *,
             fill=None, stroke="#000000", stroke_width=1,
             rounded=1, arc_size=8, font_size=10, font_color="#000000",
             bold=0, italic=0, align="center", valign="middle",
             dashed=0, html=1):
    """Rect with absolute drawio coordinates (x, y in px, top-left origin)."""
    cid = nid()
    style = cell_style(
        rounded=rounded, arcSize=arc_size,
        whiteSpace="wrap", html=html,
        fillColor=fill, strokeColor=stroke, strokeWidth=stroke_width,
        fontSize=font_size, fontColor=font_color,
        fontStyle=(1 if bold else 0) + (2 if italic else 0),
        horizontal=1, align=align, verticalAlign=valign,
        dashed=dashed,
    )
    geom = f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
    cell = f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">{geom}</mxCell>'
    return cell, cid


def arrow_cell(src_id, tgt_id, label="", *,
               color="#000000", stroke_width=1, dashed=0,
               entry="", exit="", font_size=9, font_color="#000000",
               align="center", valign="middle"):
    cid = nid()
    sty = cell_style(
        edgeStyle="orthogonalEdgeStyle",
        rounded=0, orthogonalLoop=1, jettySize="auto", html=1,
        strokeColor=color, strokeWidth=stroke_width,
        dashed=dashed, dashPattern="5 3" if dashed else None,
        entryX=entry, entryY="0.5" if entry else None,
        exitX=exit, exitY="0.5" if exit else None,
        fontSize=font_size, fontColor=font_color,
        align=align, verticalAlign=valign,
    )
    geom = '<mxGeometry relative="1" as="geometry"><mxPoint x="0" y="0" as="sourcePoint"/><mxPoint x="1" y="1" as="targetPoint"/></mxGeometry>'
    cell = f'<mxCell id="{cid}" value="{escape(label)}" style="{sty}" edge="1" parent="1" source="{src_id}" target="{tgt_id}">{geom}</mxCell>'
    return cell, cid


def line_arrow(x1, y1, x2, y2, label="", *,
               color="#000000", stroke_width=1, dashed=0,
               start_arrow="none", end_arrow="classic",
               font_size=9, font_color="#000000"):
    """Free-hand arrow with absolute coordinates."""
    cid = nid()
    start = f"startArrow={start_arrow};startFill=1;" if start_arrow != "none" else ""
    end = f"endArrow={end_arrow};endFill=1;" if end_arrow != "none" else ""
    sty = cell_style(
        edgeStyle="orthogonalEdgeStyle",
        rounded=0, orthogonalLoop=1, jettySize="auto", html=1,
        strokeColor=color, strokeWidth=stroke_width,
        dashed=dashed, dashPattern="5 3" if dashed else None,
        fontSize=font_size, fontColor=font_color,
        **(dict(startArrow=start_arrow, startFill=1) if start_arrow != "none" else {}),
        **(dict(endArrow=end_arrow, endFill=1) if end_arrow != "none" else {}),
    )
    geom = f'<mxGeometry x="0" y="0" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/><mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry>'
    cell = f'<mxCell id="{cid}" value="{escape(label)}" style="{sty}" edge="1" parent="1">{geom}</mxCell>'
    return cell, cid


def text_label(dx, dy, text, *, font_size=10, font_color="#000000",
               bold=0, italic=0, align="center", valign="middle",
               html=1, bg=None):
    """Standalone text label at matplotlib data coordinates (dx, dy)."""
    cid = nid()
    px, py = d2x(dx), d2y(dy)
    style = cell_style(
        text=1, html=html,
        fontSize=font_size, fontColor=font_color,
        fontStyle=(1 if bold else 0) + (2 if italic else 0),
        align=align, verticalAlign=valign,
        labelBackgroundColor=bg,
    )
    geom = f'<mxGeometry x="{px}" y="{py}" width="1" height="1" as="geometry"/>'
    cell = f'<mxCell id="{cid}" value="{escape(text)}" style="{style}" vertex="1" parent="1">{geom}</mxCell>'
    return cell, cid


# ── main ────────────────────────────────────────────────────────────────

def generate():
    cells = []
    add_cell = lambda c: cells.append(c[0] if isinstance(c, tuple) else c)
    cid = {}  # named references

    # ── Background tiers ──────────────────────────────────────────────
    # Privacy banner
    c, ci = rect_cell(0.4, 15.1, 21.2, 0.7,
                      "[Privacy] PIPL: raw audio never leaves the device; "
                      "only the 128-d non-invertible F_v is transmitted (LDP ε=1.5)",
                      fill="#EAF2FB", stroke="#1f4060", font_size=10,
                      font_color="#1f4060", bold=1, arc_size=10)
    add_cell(c); cid["privacy"] = ci

    # Input row
    c, ci = rect_cell(0.4, 13.9, 21.2, 1.0,
                      "<b>Input modalities</b>",
                      fill="#FFFFFF", stroke="#1f4060", font_size=10,
                      font_color="#1f4060", arc_size=10)
    add_cell(c); cid["input_row"] = ci

    # Tier 1
    c, ci = rect_cell(0.4, 10.0, 21.2, 3.7,
                      '<b>Tier 1: On-device detection</b><br><i>(EDGE)</i>',
                      fill="#F0F9F4", stroke="#2ca02c", stroke_width=1.4,
                      font_size=10.5, font_color="#2ca02c", arc_size=12,
                      valign="top")
    add_cell(c); cid["tier1"] = ci

    # T1 sidebar (text labels only)
    for lab, yy in [("• ~12 ms feat. extraction", 12.30),
                    ("• ~240 MB (Q4_K_M)", 11.95),
                    ("• Snapdragon 8 Gen 3", 11.60)]:
        add_cell(text_label(0.55, yy, lab, font_size=7.3, font_color="#333",
                            align="left"))

    # Tier 2
    c, ci = rect_cell(0.4, 5.0, 21.2, 3.2,
                      '<b>Tier 2: Cloud reasoning</b><br><i>(async conditional trigger)</i>',
                      fill="#F0F6FC", stroke="#1f77b4", stroke_width=1.4,
                      font_size=10.5, font_color="#1f77b4", arc_size=12,
                      valign="top")
    add_cell(c); cid["tier2"] = ci

    for lab, yy in [("• ~268 ms (P50 latency)", 7.95),
                    ("• ~342 ms (P99 latency)", 7.60),
                    ("• GPU: H100 80GB  • NVFP4", 7.25)]:
        add_cell(text_label(0.55, yy, lab, font_size=7.3, font_color="#333",
                            align="left"))

    # Tier 3
    c, ci = rect_cell(0.4, 0.6, 19.4, 3.6,
                      '<b>Tier 3: Multimodal risk fusion</b><br><i>(EDGE)</i>',
                      fill="#FFF8F0", stroke="#ff7f0e", stroke_width=1.4,
                      font_size=10.5, font_color="#ff7f0e", arc_size=12,
                      valign="top")
    add_cell(c); cid["tier3"] = ci

    for lab, yy in [("• Latency: ~1 ms", 3.90),
                    ("• Optimiser: L-BFGS", 3.55),
                    ("• Linear Sigmoid fusion", 3.20)]:
        add_cell(text_label(0.55, yy, lab, font_size=7.3, font_color="#333",
                            align="left"))

    # ── Input modality icons ──────────────────────────────────────────
    inputs = [
        (4.85, "■", "SMS",   "#2ca02c"),
        (8.65, "◆", "URL links",  "#9467bd"),
        (12.45,"▶", "Voice call", "#1f77b4"),
        (16.25,"●", "Call metadata", "#ff7f0e"),
    ]
    for ix, icon, ilab, iclr in inputs:
        add_cell(text_label(ix, 14.4, icon, font_size=14, font_color=iclr))
        add_cell(text_label(ix+0.30, 14.4, ilab, font_size=9,
                            font_color="#444", align="left"))

    # ── Tier 1 sub-modules ────────────────────────────────────────────
    # Each: (x, w, icon, color, title, subtitle, body_lines)
    mods_t1 = [
        (3.60, 2.50, "■",  "#2ca02c", "SMS module",     "text analysis",
         ["12-d text feat."]),
        (6.60, 2.50, "◆",  "#9467bd", "URL module",      "structural analysis",
         ["6-d struct. feat."]),
        (10.70, 3.50, "≈", "#1f77b4", "Acoustic module", "Whisper-tiny encoder",
         ["128-d F_v (MFCC+Whisper)", "Whisper-tiny w/o decoder head",
          "(LDP ε=1.5)"]),
        (14.50, 3.50, "★", "#cc5500", "On-device model", "(Q4_K_M Student)",
         ["Qwen2.5-0.5B", "Draft: Qwen2-0.1B (124M)",
          "Spec-decode α=0.86", "3.32× speedup (SD8G3)"]),
        (18.30, 3.50, "✓", "#2ca02c", "Local risk score","(Fast Path)",
         ["high-confidence cases (r ≥ 0.70):", "direct low-latency verdict"]),
    ]
    Y1, H1 = 10.30, 2.40
    for mx, mw, mic, mclr, mtitle, msub, mbody in mods_t1:
        body_html = "".join(f"{line}<br>" for line in mbody)
        label = (f"<b>{mic} {mtitle}</b><br>"
                 f"<span style='color:#666'>{msub}</span><hr size='1'>"
                 f"{body_html}")
        c, ci = rect_cell(mx, Y1, mw, H1, label,
                          fill="#FFFFFF", stroke="#2ca02c",
                          font_size=8, font_color="#222",
                          arc_size=8, valign="top")
        add_cell(c)
        cid.setdefault("t1_mods", []).append(ci)

    # ── Input → T1 arrows ─────────────────────────────────────────────
    target_xs = [4.85, 7.85, 12.45, 16.25]
    for i, (ix, tx) in enumerate(zip([4.85, 8.65, 12.45, 16.25], target_xs)):
        if len(cid.get("t1_mods", [])) > i:
            c, ci = arrow_cell(cid["input_row"], cid["t1_mods"][i], "",
                               color="#888", stroke_width=0.8)
            add_cell(c)

    # ── Inter-tier flows T1→T2 ────────────────────────────────────────
    # F_v upload arrow (from Acoustic module to Tier 2)
    c, ci = line_arrow(d2x(10.70+3.50/2), d2y(10.30),
                       d2x(10.70+3.50/2), d2y(8.20)+8,
                       "F_v upload (ε=1.5 LDP)",
                       color="#1f77b4", stroke_width=1.2, font_size=8,
                       font_color="#1f77b4")
    add_cell(c)

    # Async trigger (from On-device model to Tier 2)
    c, ci = line_arrow(d2x(14.50+3.50/2), d2y(10.30),
                       d2x(14.50+3.50/2), d2y(8.20)+8,
                       "async conditional trigger\n(medium confidence: 0.35 ≤ r < 0.70)",
                       color="#888", stroke_width=1.2, font_size=7.5)
    add_cell(c)

    # ── Tier 2 sub-modules ────────────────────────────────────────────
    Y2, H2 = 5.30, 2.10
    mods_t2 = [
        (2.60, 4.40, "▷", "#1f77b4", "CoT reasoning", "chain-of-thought",
         ["step-wise risk analysis"]),
        (8.20, 5.00, "■", "#1f77b4", "Cloud model", "(NVFP4 + OV-Freeze)",
         ["Qwen2.5-0.5B (QAD)", "99.1% BF16 recovery"]),
        (14.60, 3.50, "●", "#1f77b4", "Federated aggregator",
         "privacy-preserving", ["cross-user knowledge", "no raw data uploaded"]),
    ]
    for mx, mw, mic, mclr, mtitle, msub, mbody in mods_t2:
        body_html = "".join(f"{line}<br>" for line in mbody)
        label = (f"<b>{mic} {mtitle}</b><br>"
                 f"<span style='color:#666'>{msub}</span><hr size='1'>"
                 f"{body_html}")
        c, ci = rect_cell(mx, Y2, mw, H2, label,
                          fill="#FFFFFF", stroke="#1f77b4",
                          font_size=8, font_color="#222",
                          arc_size=8, valign="top")
        add_cell(c)
        cid.setdefault("t2_mods", []).append(ci)

    # Intra-T2 arrows: CoT → Cloud → Federated
    for i in range(len(mods_t2)-1):
        if len(cid.get("t2_mods", [])) > i+1:
            c, ci = arrow_cell(cid["t2_mods"][i], cid["t2_mods"][i+1], "",
                               color="#666", stroke_width=1.0)
            add_cell(c)

    # ── T2 → T3 arrow: r_cloud ────────────────────────────────────────
    cloud_center_x = 8.20 + 5.00/2
    c, ci = line_arrow(d2x(cloud_center_x), d2y(5.30),
                       d2x(cloud_center_x), d2y(4.20)-10,
                       "r_cloud",
                       color="#1f77b4", stroke_width=1.2)
    add_cell(c)

    # ── Tier 3 risk blocks ────────────────────────────────────────────
    risk_blocks = [
        (3.10, "■", "#2ca02c", "Text risk r_text", "(from Tier 1/2)", "weight w = 0.40"),
        (7.00, "≈", "#1f77b4", "Audio risk r_audio", "(from Tier 1/2)", "weight w = 0.30"),
        (10.90,"◆", "#9467bd", "URL risk r_url", "(from Tier 1/2)", "weight w = 0.20"),
        (14.80,"●", "#ff7f0e", "Meta risk r_meta", "(from Tier 1)", "weight w = 0.10"),
    ]
    RY, RH = 2.00, 1.60
    for rx, ric, rclr, rtitle, rsub, rwt in risk_blocks:
        label = (f"<b>{ric} {rtitle}</b><br>"
                 f"<span style='color:#666'>{rsub}</span><hr size='1'>"
                 f"{rwt}")
        c, ci = rect_cell(rx, RY, 3.70, RH, label,
                          fill="#FFFFFF", stroke="#ff7f0e",
                          font_size=8, font_color="#222",
                          arc_size=8, valign="top")
        add_cell(c)
        cid.setdefault("t3_mods", []).append(ci)

    # ── Fusion equation bar ──────────────────────────────────────────
    label_fusion = (
        "<b>Risk fusion (Sigmoid linear weighting)</b><br>"
        "r = σ(w<sub>text</sub>·r<sub>text</sub> + "
        "w<sub>audio</sub>·r<sub>audio</sub> + "
        "w<sub>url</sub>·r<sub>url</sub> + "
        "w<sub>meta</sub>·r<sub>meta</sub> + b)<br>"
        "<span style='font-size:9px'>Verdict: Safe / Medium / High</span>"
    )
    c, ci = rect_cell(3.10, 0.60, 15.40, 1.20, label_fusion,
                      fill="#FFF4E6", stroke="#ff7f0e",
                      font_size=9, font_color="#222",
                      arc_size=8)
    add_cell(c); cid["fusion"] = ci

    # Risk blocks → Fusion bar arrows
    for i in range(len(risk_blocks)):
        if len(cid.get("t3_mods", [])) > i:
            c, ci = arrow_cell(cid["t3_mods"][i], cid["fusion"], "",
                               color="#888", stroke_width=0.9)
            add_cell(c)

    # ── Alert box ────────────────────────────────────────────────────
    label_alert = "<b>!</b><br><b>Risk alert</b><br><i>(ALERT)</i>"
    c, ci = rect_cell(20.0, 0.70, 1.55, 1.55, label_alert,
                      fill="#FFFFFF", stroke="#d62728", stroke_width=1.5,
                      font_size=9, font_color="#d62728", arc_size=10)
    add_cell(c); cid["alert"] = ci

    # Fusion → Alert arrow
    c, ci = arrow_cell(cid["fusion"], cid["alert"], "",
                       color="#d62728", stroke_width=1.4)
    add_cell(c)

    # ── Fast Path (3-segment) ────────────────────────────────────────
    fp_sx, fp_sy = d2x(20.05), d2y(10.30)
    fp_ex, fp_ey = d2x(21.2), d2y(10.30)
    fp_ey2 = d2y(1.50)
    # 3 segments drawn as free arrows
    c, ci = line_arrow(fp_sx, fp_sy, fp_ex, fp_ey,
                       "", color="#2ca02c", stroke_width=1.3,
                       dashed=1, start_arrow="none", end_arrow="none")
    add_cell(c)
    c, ci = line_arrow(fp_ex, fp_ey, fp_ex, fp_ey2,
                       "", color="#2ca02c", stroke_width=1.3,
                       dashed=1, start_arrow="none", end_arrow="none")
    add_cell(c)
    c, ci = line_arrow(fp_ex-3, fp_ey2, fp_ex+3, fp_ey2,
                       "r_local", color="#2ca02c", stroke_width=1.3,
                       dashed=1, start_arrow="none", end_arrow="classic")
    add_cell(c)

    # ── Legend ───────────────────────────────────────────────────────
    c, ci = rect_cell(0.4, -0.15, 13.0, 0.60,
                      '<b>Legend:</b>  → Data flow  - - - High-confidence fast path  - - - Cloud data flow',
                      fill="#F8F8F8", stroke="#888", stroke_width=0.5,
                      font_size=7.8, font_color="#333", arc_size=5,
                      align="left")
    add_cell(c)

    # Legend color swatches
    for lx, lclr, ltxt in [(14.10, "#2ca02c", "Edge"),
                           (16.40, "#1f77b4", "Cloud"),
                           (18.90, "#ff7f0e", "Fusion & decision")]:
        # Colored rectangle
        c, ci = rect_abs(d2x(lx), d2y(-0.15)-3, 19, 10,
                         "", fill="white", stroke=lclr,
                         font_size=1, arc_size=0)
        add_cell(c)
        add_cell(text_label(lx+0.55, -0.15, ltxt, font_size=7.8,
                            font_color="#333", align="left"))

    # Abbreviation glossary
    add_cell(text_label(
        0.7, -0.55,
        "Abbrev.:  LDP = Local Differential Privacy;  "
        "CoT = Chain-of-Thought;  "
        "NVFP4 = 4-bit NormalFloat;  "
        "Q4_K_M = 4-bit GGUF format",
        font_size=7, font_color="#444", italic=1, align="left"))

    # ── Assemble XML ─────────────────────────────────────────────────
    page_w = d2x(22) + 30   # extra margin
    page_h = d2y(0) + 30

    cells_xml = "\n".join(cells)

    drawio = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="fig01_to_drawio.py" modified="{__import__('datetime').datetime.now().isoformat()}" version="24.0.0">
  <diagram id="fig01" name="Page-1">
    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10"
                  guides="1" tooltips="1" connect="1" arrows="1"
                  fold="1" page="1" pageScale="1"
                  pageWidth="{page_w}" pageHeight="{page_h}" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "fig01_architecture_en.drawio")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(drawio)
    print(f"Saved {out_path}  ({len(cells)} cells)")


if __name__ == "__main__":
    generate()

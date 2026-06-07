"""Figure 1: QAD-MultiGuard three-tier edge-cloud architecture.

Comprehensive system diagram showing:
  - PIPL §23 privacy constraint banner (top)
  - Four input modalities (SMS / Voice Call / URL Links / Call Metadata)
  - Tier 1 (Edge): 5 on-device modules + Fast Path
  - Tier 2 (Cloud): CoT inference + NVFP4+OVF model + Federated aggregator
  - Tier 3 (Fusion): 4 per-modality risk scores + L-BFGS Sigmoid fusion + Alert
  - Cross-tier data flows: F_v upload (DP), Fast Path
  - Legend + abbreviation glossary (bottom)

Paper-aligned fixes (v5):
  - OV-Freeze merged into Cloud model (not a standalone runtime component)
  - Fusion formula uses sigmoid: r = sigma(sum w_m * r_m + b)
  - Sidebar latency numbers match paper (S3-C1): T1 feat. extraction ~12 ms,
    T2 P50=268 ms / P99=342 ms
  - Spec-decode: 3.32x on SD8G3 with draft model Qwen2-0.1B (124M)
  - Acoustic module: Whisper-tiny encoder w/o decoder head
  - Fast Path arrow routed to avoid T2 Federated aggregator overlap
"""
import os
import sys
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

import sci_style as sci  # noqa: E402

# Ensure output directory exists (work from any CWD)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_output_dir = os.path.join(_script_dir, "output")
os.makedirs(_output_dir, exist_ok=True)

# CJK font setup
mpl.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
mpl.rcParams["font.family"] = "sans-serif"
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["mathtext.fontset"] = "stix"

# Color palette
C_EDGE_FC   = "#FFFFFF"
C_EDGE_EC   = "#2ca02c"
C_EDGE_BG   = "#F0F9F4"
C_CLOUD_FC  = "#FFFFFF"
C_CLOUD_EC  = "#1f77b4"
C_CLOUD_BG  = "#F0F6FC"
C_FUSION_FC = "#FFFFFF"
C_FUSION_EC = "#ff7f0e"
C_FUSION_BG = "#FFF8F0"
C_ALERT     = "#d62728"
C_PRIVACY   = "#1f4060"
C_INPUT     = "#444"

fig, ax = plt.subplots(figsize=(11.0, 8.0))
ax.set_xlim(0, 22)
ax.set_ylim(0, 16)
ax.axis("off")

# Private helper: LaTeX strings in non-raw regular strings must use double
# backslash (e.g. "\\alpha") to survive Python 3.14+ strict escape checking.
# For readability we define a small wrapper.
L = lambda s: s  # noqa: just a passthrough for future-proofing

# ═══════════════════════════════════════════════════════════════════════
# Privacy banner (top)  PIPL Article 23 constraint
# ═══════════════════════════════════════════════════════════════════════
banner = FancyBboxPatch(
    (0.4, 15.1), 21.2, 0.7,
    boxstyle="round,pad=0.04,rounding_size=0.10",
    fc="#EAF2FB", ec=C_PRIVACY, lw=1.0
)
ax.add_patch(banner)
ax.text(
    11.0, 15.45,
    r"[Privacy] PIPL: raw audio never leaves the device; "
    r"only the 128-d non-invertible $\mathbf{F}_v$ is transmitted (LDP $\epsilon{=}1.5$)",
    ha="center", va="center", fontsize=10, color=C_PRIVACY, weight="bold"
)

# ═══════════════════════════════════════════════════════════════════════
# Input modalities row
# ═══════════════════════════════════════════════════════════════════════
input_box = FancyBboxPatch(
    (0.4, 13.9), 21.2, 1.0,
    boxstyle="round,pad=0.04,rounding_size=0.10",
    fc="#FFFFFF", ec=C_PRIVACY, lw=1.0
)
ax.add_patch(input_box)
ax.text(
   2, 14.4, "Input modalities",
    fontsize=10, weight="bold", ha="center", va="center", color=C_PRIVACY
)

# Four input icons + labels
inputs = [
    (4.85,  "■", "SMS",  "#2ca02c"),
    (8.65,  "◆", "URL links",    "#9467bd"),
    (12.45, "▶", "Voice call",    "#1f77b4"),
    (16.25, "●", "Call metadata","#ff7f0e"),
]
for x, icon, label, color in inputs:
    ax.text(x, 14.4, icon, fontsize=14, va="center", ha="center", color=color)
    ax.text(x + 0.30, 14.4, label, fontsize=9, va="center",
            ha="left", color=C_INPUT)

# ═══════════════════════════════════════════════════════════════════════
# TIER 1  Edge
# ═══════════════════════════════════════════════════════════════════════
T1_Y = 10.00
T1_H = 3.70
t1 = FancyBboxPatch(
    (0.4, T1_Y), 21.2, T1_H,
    boxstyle="round,pad=0.06,rounding_size=0.12",
    fc=C_EDGE_BG, ec=C_EDGE_EC, lw=1.4
)
ax.add_patch(t1)
ax.text(3, 13.2, "Tier 1: On-device detection",
        fontsize=10.5, weight="bold", ha="center", va="center", color=C_EDGE_EC)
ax.text(1.4, 12.55, "(EDGE)", fontsize=8.5,
        ha="center", va="center", color=C_EDGE_EC, style="italic")

# Sidebar specs
ax.text(0.55, 12.2, "• ~12 ms feat. extraction",
        fontsize=7.3, ha="left", va="center", color="#333")
ax.text(0.55, 11.85, "• ~240 MB (Q4_K_M)",
        fontsize=7.3, ha="left", va="center", color="#333")
ax.text(0.55, 11.50, "• Snapdragon 8 Gen 3",
        fontsize=7.3, ha="left", va="center", color="#333")

T1_SUB_Y = 10.30
T1_SUB_H = 2.40


def tier_block(x, y, w, h, title_icon, title, subtitle, body_lines,
               ec="#222", fc="#FFFFFF", icon_color="#222"):
    """Draw a tier sub-block with icon, title, divider, body lines."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        fc=fc, ec=ec, lw=1.0
    ))
    # Title row
    ax.text(x + 0.3, y + h - 0.30, title_icon,
            fontsize=11, va="center", ha="center", color=icon_color)
    ax.text(x + w / 2 + 0.15, y + h - 0.28, title, fontsize=9,
            weight="bold", ha="center", va="center", color="#222")
    if subtitle:
        ax.text(x + w / 2 + 0.15, y + h - 0.58, subtitle, fontsize=7.5,
                ha="center", va="center", color="#666")
    # Divider
    ax.plot([x + 0.15, x + w - 0.15], [y + h - 0.78, y + h - 0.78],
            color="#bbb", lw=0.5, ls="--")
    # Body
    for i, line in enumerate(body_lines):
        ax.text(x + w / 2, y + h - 1.08 - i * 0.30, line, fontsize=7.8,
                ha="center", va="center", color="#222")


W_BLOCK = 3.50

# Tier-1 modules  (x, icon, color, title, subtitle, body_lines, width)
mods_t1 = [
    (3.60,  "■", "#2ca02c", "SMS module",     "text analysis",
     ["12-d text feat."], 2.50),
    (6.60,  "◆", "#9467bd", "URL module",      "structural analysis",
     ["6-d struct. feat."], 2.50),
    (10.70, "≈", "#1f77b4", "Acoustic module", "Whisper-tiny encoder",
     [r"128-d $\mathbf{F}_v$ (MFCC+Whisper)", "Whisper-tiny w/o decoder head",
      r"(LDP $\epsilon{=}1.5$)"], 3.50),
    (14.50, "★", "#cc5500", "On-device model", "(Q4_K_M Student)",
     ["Qwen2.5-0.5B",
      "Draft: Qwen2-0.1B (124M)",
      r"Spec-decode $\alpha{=}0.86$",
      r"3.32$\times$ speedup (SD8G3)"], 3.50),
    (18.30, "✓", "#2ca02c", "Local risk score","(Fast Path)",
     [r"high-confidence cases ($r \geq 0.70$):",
      "direct low-latency verdict"], 3.50),
]
for x, icon, ic_color, title, sub, body, w in mods_t1:
    tier_block(x, T1_SUB_Y, w, T1_SUB_H, icon, title, sub, body,
               ec=C_EDGE_EC, icon_color=ic_color)

# Input  Tier-1 arrows
input_xs  = [4.85, 8.65, 12.45, 16.25]
target_xs = [4.85, 7.85, 12.45, 16.25]
for in_x, mod_x in zip(input_xs, target_xs):
    ax.annotate("", xy=(mod_x, T1_SUB_Y + T1_SUB_H),
                xytext=(in_x, 13.85),
                arrowprops=dict(arrowstyle="->", lw=0.8, color="#888"))

# ═══════════════════════════════════════════════════════════════════════
# Inter-tier flow labels  T1  T2
# ═══════════════════════════════════════════════════════════════════════
T2_Y = 5.00
T2_H = 3.20
T2_TOP = T2_Y + T2_H
T1_BOTTOM = T1_Y
GAP_T1_T2 = T1_BOTTOM - T2_TOP

# F_v upload arrow (LDP)
fv_x = 10.70 + W_BLOCK / 2  # centre of Acoustic module
ax.annotate("", xy=(fv_x, T2_TOP + 0.15), xytext=(fv_x, T1_SUB_Y),
            arrowprops=dict(arrowstyle="->", lw=1.2, color=C_CLOUD_EC))
ax.text(12.50, T2_TOP + 1.05,
        r"$\mathbf{F}_v$ upload ($\epsilon{=}1.5$ LDP)",
        fontsize=8, ha="center", va="center", color=C_CLOUD_EC, weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", pad=1))

# Async trigger
at_x = 14.50 + W_BLOCK / 2  # centre of On-device model
ax.annotate("", xy=(at_x, T2_TOP + 0.15), xytext=(at_x, T1_SUB_Y),
            arrowprops=dict(arrowstyle="->", lw=1.2, color="#888"))
ax.text(16.30, T2_TOP + 1.05,
        "async conditional trigger\n"
        r"(medium confidence: $0.35 \leq r < 0.70$)",
        fontsize=7.5, ha="center", va="center", color="#333",
        bbox=dict(facecolor="white", edgecolor="none", pad=1))

# Fast Path  routed along right edge to avoid T2 Federated aggregator
FP_START = (18.30 + W_BLOCK / 2, T1_SUB_Y)    # (20.05, 10.30)
FP_ELBOW = (21.2, T1_SUB_Y)
FP_END_Y = 1.50

# Segment 1: horizontal right
ax.plot([FP_START[0], FP_ELBOW[0]], [FP_START[1], FP_ELBOW[1]],
        color=C_EDGE_EC, lw=1.3, ls=(0, (5, 3)))
# Segment 2: vertical down
ax.plot([FP_ELBOW[0], FP_ELBOW[0]], [FP_ELBOW[1], FP_END_Y],
        color=C_EDGE_EC, lw=1.3, ls=(0, (5, 3)))
# Segment 3: arrowhead into Alert
ax.annotate("", xy=(21.55, FP_END_Y), xytext=(FP_ELBOW[0], FP_END_Y),
            arrowprops=dict(arrowstyle="->", lw=1.3, color=C_EDGE_EC))
ax.text(21.3, T2_TOP + 0.50, r"$r_{\rm local}$",
        fontsize=8.5, ha="center", va="center", color=C_EDGE_EC, weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", pad=1))

# ═══════════════════════════════════════════════════════════════════════
# TIER 2  Cloud  3 blocks: CoT  Cloud+OVF  Federated
# ═══════════════════════════════════════════════════════════════════════
t2 = FancyBboxPatch(
    (0.4, T2_Y), 21.2, T2_H,
    boxstyle="round,pad=0.06,rounding_size=0.12",
    fc=C_CLOUD_BG, ec=C_CLOUD_EC, lw=1.4
)
ax.add_patch(t2)
ax.text(1.4, T2_TOP - 0.45, "Tier 2: Cloud reasoning",
        fontsize=10.5, weight="bold", ha="center", va="center", color=C_CLOUD_EC)
ax.text(1.4, T2_TOP - 0.80, "(async conditional trigger)",
        fontsize=8.5, ha="center", va="center", color=C_CLOUD_EC, style="italic")

# Sidebar specs
ax.text(0.55, T2_TOP - 1.25, "• ~268 ms (P50 latency)",
        fontsize=7.3, ha="left", va="center", color="#333")
ax.text(0.55, T2_TOP - 1.60, "• ~342 ms (P99 latency)",
        fontsize=7.3, ha="left", va="center", color="#333")
ax.text(0.55, T2_TOP - 1.95, "• GPU: H100 80GB  • NVFP4",
        fontsize=7.3, ha="left", va="center", color="#333")

T2_SUB_Y = T2_Y + 0.30
T2_SUB_H = 2.10

# Each entry: (x, icon, color, title, subtitle, body_lines, width)
mods_t2 = [
    (2.60,  "▷", "#1f77b4", "CoT reasoning",       "chain-of-thought",
     ["step-wise risk analysis"], 4.40),
    (8.20,  "■", "#1f77b4", "Cloud model",          "(NVFP4 + OV-Freeze)",
     ["Qwen2.5-0.5B (QAD)", "99.1% BF16 recovery"], 5.00),
    (14.60, "●", "#1f77b4", "Federated aggregator", "privacy-preserving",
     ["cross-user knowledge", "no raw data uploaded"], 3.50),
]
for x, icon, ic_color, title, sub, body, w in mods_t2:
    tier_block(x, T2_SUB_Y, w, T2_SUB_H, icon, title, sub, body,
               ec=C_CLOUD_EC, icon_color=ic_color)

# Intra-T2 arrows: CoT  Cloud  Federated
t2_links = [
    ((2.60, 4.40), (8.20, 5.00)),
    ((8.20, 5.00), (14.60, 3.50)),
]
for (x1, w1), (x2, w2) in t2_links:
    ax.annotate("", xy=(x2, T2_SUB_Y + T2_SUB_H / 2),
                xytext=(x1 + w1, T2_SUB_Y + T2_SUB_H / 2),
                arrowprops=dict(arrowstyle="->", lw=1.0, color="#666"))

# ═══════════════════════════════════════════════════════════════════════
# Inter-tier T2  T3
# ═══════════════════════════════════════════════════════════════════════
T3_Y = 0.60
T3_H = 3.60
T3_TOP = T3_Y + T3_H

# r_cloud arrow
ccx = 8.20 + 5.00 / 2   # Cloud model centre = 10.70
ax.annotate("", xy=(ccx, T3_TOP + 0.40), xytext=(ccx, T2_SUB_Y),
            arrowprops=dict(arrowstyle="->", lw=1.2, color=C_CLOUD_EC))
ax.text(ccx + 1.00, T3_TOP + 1.10, r"$r_{\rm cloud}$",
        fontsize=9, ha="center", va="center", color=C_CLOUD_EC, weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", pad=1))

# ═══════════════════════════════════════════════════════════════════════
# TIER 3  Fusion
# ═══════════════════════════════════════════════════════════════════════
t3 = FancyBboxPatch(
    (0.4, T3_Y), 19.4, T3_H,
    boxstyle="round,pad=0.06,rounding_size=0.12",
    fc=C_FUSION_BG, ec=C_FUSION_EC, lw=1.4
)
ax.add_patch(t3)
ax.text(1.4, T3_TOP - 0.30, "Tier 3: Multimodal risk fusion",
        fontsize=10.5, weight="bold", ha="center", va="center", color=C_FUSION_EC)
ax.text(1.4, T3_TOP - 0.65, "(EDGE)", fontsize=8.5,
        ha="center", va="center", color=C_FUSION_EC, style="italic")

# Sidebar specs
ax.text(0.55, T3_TOP - 1.30, "• Latency: ~1 ms",
        fontsize=7.3, ha="left", va="center", color="#333")
ax.text(0.55, T3_TOP - 1.65, "• Optimiser: L-BFGS",
        fontsize=7.3, ha="left", va="center", color="#333")
ax.text(0.55, T3_TOP - 2.00, "• Linear Sigmoid fusion",
        fontsize=7.3, ha="left", va="center", color="#333")

# 4 risk-score input blocks
RISK_Y = 2.00
RISK_H = 1.60
risk_blocks = [
    (3.10,  "■", "#2ca02c", r"Text risk $r_{\rm text}$",
     "(from Tier 1/2)", "weight $w = 0.40$"),
    (7.00,  "≈", "#1f77b4", r"Audio risk $r_{\rm audio}$",
     "(from Tier 1/2)", "weight $w = 0.30$"),
    (10.90, "◆", "#9467bd", r"URL risk $r_{\rm url}$",
     "(from Tier 1/2)", "weight $w = 0.20$"),
    (14.80, "●", "#ff7f0e", r"Meta risk $r_{\rm meta}$",
     "(from Tier 1)",   "weight $w = 0.10$"),
]
W_RISK = 3.70
for x, icon, ic_color, title, sub, wt in risk_blocks:
    ax.add_patch(FancyBboxPatch(
        (x, RISK_Y), W_RISK, RISK_H,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        fc=C_FUSION_FC, ec=C_FUSION_EC, lw=0.9
    ))
    ax.text(x + 0.30, RISK_Y + RISK_H - 0.30, icon,
            fontsize=11, va="center", ha="center", color=ic_color)
    ax.text(x + W_RISK / 2 + 0.15, RISK_Y + RISK_H - 0.30, title,
            fontsize=9, weight="bold", ha="center", va="center", color="#222")
    ax.text(x + W_RISK / 2, RISK_Y + RISK_H - 0.65, sub,
            fontsize=7, ha="center", va="center", color="#666")
    ax.plot([x + 0.15, x + W_RISK - 0.15],
            [RISK_Y + RISK_H - 0.95, RISK_Y + RISK_H - 0.95],
            color="#bbb", lw=0.5, ls="--")
    ax.text(x + W_RISK / 2, RISK_Y + RISK_H - 1.40, wt,
            fontsize=8.5, ha="center", va="center", color="#cc5500",
            weight="bold")

# Fusion equation bar
FB_Y = 0.60
FB_H = 1.20
fb = FancyBboxPatch(
    (3.10, FB_Y), 15.40, FB_H,
    boxstyle="round,pad=0.04,rounding_size=0.08",
    fc="#FFF4E6", ec=C_FUSION_EC, lw=1.0
)
ax.add_patch(fb)
ax.text(10.80, FB_Y + FB_H - 0.30,
        "Risk fusion (Sigmoid linear weighting)",
        fontsize=9.5, weight="bold", ha="center", va="center", color="#8a4a00")
# The fusion formula uses a raw multiline string to survive Python 3.14 checks
ax.text(10.80, FB_Y + FB_H - 0.70,
        (r"$r = \sigma(w_{\text{text}} r_{\text{text}} + "
         r"w_{\text{audio}} r_{\text{audio}} + "
         r"w_{\text{url}} r_{\text{url}} + "
         r"w_{\text{meta}} r_{\text{meta}} + b)$"),
        fontsize=9, ha="center", va="center", color="#222")
ax.text(10.80, FB_Y + 0.22,
        r"Verdict:  $\;$ Safe  /  Medium  /  High",
        fontsize=7.5, ha="center", va="center", color="#333")

# Risk blocks  fusion bar
for x, _, _, _, _, _ in risk_blocks:
    ax.annotate("", xy=(x + W_RISK / 2, FB_Y + FB_H),
                xytext=(x + W_RISK / 2, RISK_Y),
                arrowprops=dict(arrowstyle="->", lw=0.9, color="#888"))

# ═══════════════════════════════════════════════════════════════════════
# Alert output  bottom-right
# ═══════════════════════════════════════════════════════════════════════
alert = FancyBboxPatch(
    (20.0, 0.70), 1.55, 1.55,
    boxstyle="round,pad=0.04,rounding_size=0.10",
    fc="#FFFFFF", ec=C_ALERT, lw=1.5
)
ax.add_patch(alert)
ax.text(20.78, 1.85, "!", fontsize=22, ha="center", va="center",
        color=C_ALERT, weight="bold")
ax.text(20.78, 1.30, "Risk alert", fontsize=9, weight="bold",
        ha="center", va="center", color=C_ALERT)
ax.text(20.78, 0.95, "(ALERT)", fontsize=7.5,
        ha="center", va="center", color=C_ALERT, style="italic")

# Fusion  Alert
ax.annotate("", xy=(20.0, 1.20), xytext=(18.50, 1.20),
            arrowprops=dict(arrowstyle="->", lw=1.4, color=C_ALERT))

# ═══════════════════════════════════════════════════════════════════════
# Legend  bottom-left
# ═══════════════════════════════════════════════════════════════════════
LEG_Y = -0.15
LEG_H = 0.60
leg = FancyBboxPatch(
    (0.4, LEG_Y), 13.0, LEG_H,
    boxstyle="round,pad=0.03,rounding_size=0.05",
    fc="#F8F8F8", ec="#888", lw=0.5
)
ax.add_patch(leg)
ax.text(0.7, LEG_Y + LEG_H / 2, "Legend:",
        fontsize=8.5, weight="bold", ha="left", va="center", color="#333")

# Solid black arrow  data flow
ax.annotate("", xy=(3.0, LEG_Y + LEG_H / 2),
            xytext=(2.4, LEG_Y + LEG_H / 2),
            arrowprops=dict(arrowstyle="->", lw=0.9, color="#222"))
ax.text(3.10, LEG_Y + LEG_H / 2, "Data flow",
        fontsize=7.8, ha="left", va="center", color="#333")

# Dashed green  fast path
ax.plot([4.5, 5.1], [LEG_Y + LEG_H / 2, LEG_Y + LEG_H / 2],
        color=C_EDGE_EC, lw=1.0, ls=(0, (4, 2)))
ax.annotate("", xy=(5.1, LEG_Y + LEG_H / 2),
            xytext=(5.0, LEG_Y + LEG_H / 2),
            arrowprops=dict(arrowstyle="->", lw=0.9, color=C_EDGE_EC))
ax.text(5.20, LEG_Y + LEG_H / 2, "High-confidence fast path",
        fontsize=7.8, ha="left", va="center", color="#333")

# Dashed blue  cloud flow
ax.plot([9.6, 10.2], [LEG_Y + LEG_H / 2, LEG_Y + LEG_H / 2],
        color=C_CLOUD_EC, lw=1.0, ls=(0, (4, 2)))
ax.annotate("", xy=(10.2, LEG_Y + LEG_H / 2),
            xytext=(10.1, LEG_Y + LEG_H / 2),
            arrowprops=dict(arrowstyle="->", lw=0.9, color=C_CLOUD_EC))
ax.text(10.30, LEG_Y + LEG_H / 2, "Cloud data flow",
        fontsize=7.8, ha="left", va="center", color="#333")

# Tier color legend
rh = 0.22
ax.add_patch(Rectangle((14.10, LEG_Y + (LEG_H - rh) / 2), 0.4, rh,
                       fc="white", ec=C_EDGE_EC, lw=1.0))
ax.text(14.65, LEG_Y + LEG_H / 2, "Edge",
        fontsize=7.8, ha="left", va="center", color="#333")
ax.add_patch(Rectangle((16.40, LEG_Y + (LEG_H - rh) / 2), 0.4, rh,
                       fc="white", ec=C_CLOUD_EC, lw=1.0))
ax.text(16.95, LEG_Y + LEG_H / 2, "Cloud",
        fontsize=7.8, ha="left", va="center", color="#333")
ax.add_patch(Rectangle((18.90, LEG_Y + (LEG_H - rh) / 2), 0.4, rh,
                       fc="white", ec=C_FUSION_EC, lw=1.0))
ax.text(19.45, LEG_Y + LEG_H / 2, "Fusion & decision",
        fontsize=7.8, ha="left", va="center", color="#333")

# Abbreviation glossary
ax.text(0.7, LEG_Y - 0.45,
        "Abbrev.:  LDP = Local Differential Privacy;  "
        "CoT = Chain-of-Thought;  "
        "NVFP4 = 4-bit NormalFloat;  "
        "Q4_K_M = 4-bit GGUF format",
        fontsize=7, ha="left", va="center", color="#444", style="italic")

# ═══════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════
plt.tight_layout(pad=0.3)
output_path = os.path.join(_output_dir, "fig01_architecture_en.png")
sci.save(fig, output_path, w=11.0, h=8.0)
print(f"Saved {output_path}")

"""Generate the QAD-MultiGuard three-tier architecture figure (IEEE-style)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5,
                     "savefig.dpi": 400, "savefig.bbox": "tight"})

fig, ax = plt.subplots(figsize=(7.2, 4.8))
ax.set_xlim(0, 10); ax.set_ylim(0, 11); ax.axis("off")

C_EDGE="#2E5CFF"; C_CLOUD="#FF6B35"; C_FUSE="#00A878"; C_BOX="#F4F6FB"; C_LINE="#34384B"

def box(x,y,w,h,label,edge,fc=C_BOX,fs=8.0,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.12",
                 linewidth=1.3,edgecolor=edge,facecolor=fc,zorder=2))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=fs,color=C_LINE,
            zorder=3,fontweight="bold" if bold else "normal")

def arrow(x1,y1,x2,y2,color=C_LINE,style="-|>",lw=1.4,ls="-"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,mutation_scale=11,
                 linewidth=lw,color=color,linestyle=ls,zorder=1,shrinkA=2,shrinkB=2))

# ---- Banners ----
ax.text(0.15,10.55,"Tier-1: On-device (Snapdragon 8 Gen 3, Q4_K_M)",fontsize=8.5,color=C_EDGE,fontweight="bold")
ax.text(0.15,5.95,"Tier-3: On-device Multimodal Risk Fusion",fontsize=8.5,color=C_FUSE,fontweight="bold")
ax.text(0.15,2.75,"Tier-2: Cloud Deep Reasoning (Blackwell, NVFP4)",fontsize=8.5,color=C_CLOUD,fontweight="bold")

# ---- Tier-1 extractors ----
box(0.2,8.9,2.2,1.2,"Whisper-tiny enc.\n(no decoder)\n$\\rightarrow$ 64-d",C_EDGE)
box(2.7,8.9,1.8,1.2,"MFCC\ntime-avg\n$\\rightarrow$ 64-d",C_EDGE)
box(4.9,8.9,2.0,1.2,"SMS extractor\n12-d $\\rightarrow r_{text}$",C_EDGE)
box(7.3,8.9,2.4,1.2,"URL + meta\n$\\rightarrow r_{url}, r_{meta}$",C_EDGE)

# F_v + r_audio
box(0.4,7.05,3.9,0.95,"$F_v \\in \\mathbb{R}^{128}$ (non-invertible)",C_EDGE,fc="#E8EEFF",fs=8.2,bold=True)
box(4.9,7.05,2.0,0.95,"$r_{audio}$\n(4 proxy stats)",C_EDGE)

arrow(1.3,8.9,1.6,8.0,C_EDGE)
arrow(3.6,8.9,3.0,8.0,C_EDGE)
arrow(5.9,8.9,5.9,8.0,C_EDGE)

# ---- Tier-3 fusion ----
box(2.6,4.55,4.7,1.05,
    "L-BFGS sigmoid fusion: $r=\\sigma(\\sum_m w_m r_m + b)$\n$\\mathbf{w}=[0.40, 0.30, 0.20, 0.10]$",
    C_FUSE,fc="#E0FAF0",fs=8.0)
box(7.7,4.55,2.1,1.05,"Verdict\nSafe / Med / High",C_FUSE,bold=True)
arrow(7.3,5.08,7.7,5.08,C_FUSE)

arrow(2.3,7.05,3.6,5.6,C_EDGE)
arrow(5.9,7.05,5.0,5.6,C_EDGE)
arrow(8.5,8.9,6.6,5.6,C_EDGE)

# ---- Tier-2 cloud ----
box(0.5,0.6,4.0,1.5,"NVFP4 0.5B LLM cluster\nCoT reasoning on guided\nhidden states (not plaintext)",C_CLOUD,fc="#FFF0EB")
box(5.6,0.6,4.0,1.5,"Speculative decoding\n$\\alpha=0.86$, $\\gamma=5$\n$3.32\\times$ on SD8G3",C_CLOUD,fc="#FFF0EB")

# edge<->cloud channel label placed to the LEFT, away from banner
arrow(2.3,4.55,2.3,2.1,C_CLOUD,style="<|-|>",ls="--")
ax.text(0.15,3.55,"channel: $F_v$ +\n4 scalars +\nhidden states\n($\\leq$1 KB)",fontsize=7.0,color=C_CLOUD,va="center")
arrow(6.6,2.1,5.2,4.55,C_CLOUD,style="-|>",ls="--")

leg=[Line2D([0],[0],color=C_EDGE,lw=2,label="On-device (Tier-1)"),
     Line2D([0],[0],color=C_FUSE,lw=2,label="Fusion (Tier-3)"),
     Line2D([0],[0],color=C_CLOUD,lw=2,label="Cloud (Tier-2)"),
     Line2D([0],[0],color=C_CLOUD,lw=2,ls="--",label="Edge--cloud channel")]
ax.legend(handles=leg,loc="lower center",fontsize=6.8,frameon=False,ncol=2,bbox_to_anchor=(0.5,-0.08))

plt.savefig("Fig/fig1_architecture.png",dpi=400,facecolor="white")
print("saved")

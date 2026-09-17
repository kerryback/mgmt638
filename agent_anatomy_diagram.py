"""Regenerates slides/images/session08-agent-anatomy.png (Anatomy of an Agent, deck 4).

Layout: User and LLM boxes joined by an elliptical loop (blue top arc,
orange bottom arc) with numbered steps 1-5, a messages[] box in the center,
and a Tools box at the bottom connected by teal dashed arrows.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

# shoji2 palette -- see slides/shoji2.scss
DARK = "#443f4c"          # plum-dark, for the User / LLM / Tools blocks
BLUE = "#6f8497"          # blue-deep, the outbound arc
CIRCLE_BLUE = "#6f8497"
ORANGE = "#9d874a"        # darkened sand, the return arc
TEAL = "#7d9163"          # darkened sage, the tool connectors
TEXT = "#3b3842"          # ink
GRAY = "#6f6b77"          # ink-muted
BG = "#fbfbfa"            # the slide's white panel, so the figure blends in
BUTTON_FILL = "#6f8497"
BUTTON_EDGE = "#97A7B8"
MSG_FILL = "#EBEDEB"      # pale
MSG_EDGE = "#97A7B8"      # dusty blue
MSG_BLUE = "#595460"      # plum

plt.rcParams["font.family"] = "sans-serif"
# Arial, not Helvetica Neue: the theme's own fallback stack lists it, its bold
# face resolves, and it is the only local candidate carrying U+2192 (the arrows
# in the step labels).
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]

ANN_TITLE = 15      # first line of each step annotation
ANN_SUB = 12.5      # gray second line of each step annotation

fig, ax = plt.subplots(figsize=(11, 6.15), dpi=100)
ax.set_xlim(0, 11)
ax.set_ylim(0, 6.15)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

# ----- elliptical arcs -----
CX, CY = 5.5, 3.78
A = 3.6           # semi-major axis
B_TOP = 1.59      # top arc semi-minor axis
B_BOT = 1.28      # bottom arc semi-minor axis


def arc(b, deg_from, deg_to, color):
    t = np.radians(np.linspace(deg_from, deg_to, 100))
    ax.plot(CX + A * np.cos(t), CY + b * np.sin(t), color=color, lw=2.2, zorder=1)


def arc_point(b, deg):
    t = np.radians(deg)
    return (CX + A * np.cos(t), CY + b * np.sin(t))


arc(B_TOP, 168, 10, BLUE)
arc(B_BOT, -10, -170, ORANGE)
ax.annotate("", xy=arc_point(B_TOP, 10), xytext=arc_point(B_TOP, 16),
            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=2.2,
                            mutation_scale=22), zorder=1)
ax.annotate("", xy=arc_point(B_BOT, -170), xytext=arc_point(B_BOT, -164),
            arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=2.2,
                            mutation_scale=22), zorder=1)


# ----- boxes -----
def box(x, y, w, h, fill, edge=None, lw=0, z=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor=fill, edgecolor=edge if edge else fill, linewidth=lw,
        zorder=z))


box(1.0, 3.35, 1.4, 0.87, DARK)
ax.text(1.7, 3.785, "User", color="white", fontsize=17, fontweight="bold",
        ha="center", va="center", zorder=3)
box(8.6, 3.35, 1.4, 0.87, DARK)
ax.text(9.3, 3.785, "LLM", color="white", fontsize=17, fontweight="bold",
        ha="center", va="center", zorder=3)

box(3.7, 3.32, 3.6, 0.93, MSG_FILL, MSG_EDGE, lw=1.5)
ax.text(5.5, 3.99, "messages[]", color=MSG_BLUE, fontsize=16,
        fontweight="bold", ha="center", va="center", zorder=3)
ax.text(5.5, 3.70, "system + tools + user + assistant + tool_result + …",
        color=TEXT, fontsize=10.5, ha="center", va="center", zorder=3)
ax.text(5.5, 3.49, "grows each turn; includes tool calls and results",
        color=GRAY, fontsize=9, style="italic", ha="center", va="center",
        zorder=3)

# ----- numbered step circles -----
def step(num, b, deg, color):
    x, y = arc_point(b, deg)
    ax.add_patch(Circle((x, y), 0.165, facecolor=color, edgecolor="white",
                        linewidth=1.5, zorder=4))
    ax.text(x, y, str(num), color="white", fontsize=11, fontweight="bold",
            ha="center", va="center", zorder=5)


step(1, B_TOP, 136, CIRCLE_BLUE)
step(2, B_TOP, 91, CIRCLE_BLUE)
step(3, B_BOT, -35, ORANGE)
step(4, B_BOT, -80, ORANGE)
step(5, B_BOT, -125, ORANGE)

# ----- step annotations -----
ax.text(2.9, 5.26, "User types prompt", color=TEXT, fontsize=ANN_TITLE,
        fontweight="bold", ha="center", va="center", zorder=3)

ax.text(5.5, 5.98, "Send system prompt", color=TEXT, fontsize=ANN_TITLE,
        fontweight="bold", ha="center", va="center", zorder=3)
ax.text(5.5, 5.74, "+ tool definitions + history", color=GRAY,
        fontsize=ANN_SUB, ha="center", va="center", zorder=3)

ax.text(8.45, 2.70, "LLM returns", color=TEXT, fontsize=ANN_TITLE,
        fontweight="bold", ha="center", va="center", zorder=3)
ax.text(8.45, 2.46, "text OR tool call", color=GRAY, fontsize=ANN_SUB,
        ha="center", va="center", zorder=3)

ax.text(6.35, 2.16, "If tool call → execute tool", color=TEXT,
        fontsize=ANN_TITLE, fontweight="bold", ha="center", va="center",
        zorder=3)
ax.text(6.35, 1.92, "send result back, loop to step 2", color=GRAY,
        fontsize=ANN_SUB, ha="center", va="center", zorder=3)

ax.text(3.3, 2.34, "If final answer → display to user", color=TEXT,
        fontsize=ANN_TITLE, fontweight="bold", ha="center", va="center",
        zorder=3)

# ----- tools box -----
box(2.33, 0.12, 7.2, 0.98, DARK)
ax.text(5.93, 0.92, "Tools (defined as JSON, executed by the harness)",
        color=ORANGE, fontsize=12.5, fontweight="bold", ha="center",
        va="center", zorder=3)
for x, name in [(2.55, "get_financials"), (4.21, "read_10k"),
                (5.87, "run_template"), (7.53, "make_excel")]:
    box(x, 0.28, 1.52, 0.46, BUTTON_FILL, BUTTON_EDGE, lw=1, z=3)
    ax.text(x + 0.76, 0.51, name, color="white", fontsize=11,
            fontweight="bold", ha="center", va="center", zorder=4)

# ----- teal dashed connectors -----
ax.annotate("", xy=(9.3, 1.14), xytext=(9.3, 3.30),
            arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.8,
                            linestyle="--", mutation_scale=18), zorder=2)
ax.text(9.62, 2.2, "tool call", color=TEAL, fontsize=11.5, fontweight="bold",
        ha="center", va="center", rotation=90, zorder=3)

ax.annotate("", xy=(6.1, 1.74), xytext=(6.1, 1.12),
            arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.8,
                            linestyle="--", mutation_scale=18), zorder=2)
ax.text(5.92, 1.43, "result → messages[]", color=TEAL, fontsize=11.5,
        fontweight="bold", ha="right", va="center", zorder=3)

fig.savefig("slides/images/session08-agent-anatomy.png", dpi=200, facecolor=BG)
print("saved slides/images/session08-agent-anatomy.png")

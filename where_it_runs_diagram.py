"""Regenerates slides/images/session08-where-it-runs.png (Where It Runs, session 8).

Ported from ~/repos/engi610/where_it_runs_diagram.py. Same three-zone layout --
the browser, the one container holding the app and the harness, and the services
the container reaches over HTTPS -- with shoji2's palette and this deck's parts:
the DCF agent's own tools call Yahoo Finance, and the third hop is whatever MCP
server the agent is connected to.

engi610's version greys out the built-in tools, because that agent withheld
them. This one needs Bash to run the xlsx and pptx skills' scripts and Write to
produce the file, so both boxes run.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# shoji2 palette -- see slides/shoji2.scss
DARK = "#443f4c"          # plum-dark
BLUE = "#6f8497"          # blue-deep
SAGE = "#7d9163"          # darkened sage
SAND = "#9d874a"          # darkened sand
TEXT = "#3b3842"          # ink
GRAY = "#6f6b77"          # ink-muted
BG = "#fbfbfa"            # the slide's white panel
PANEL_FILL = "#eef1f4"
PANEL_EDGE = "#97A7B8"
SAGE_FILL = "#e4eadf"
SAND_FILL = "#efe9d6"

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]

# The canvas is cropped to the drawing rather than padded around it: shoji2 caps
# figures at max-height 470px, so every empty unit here is content the slide
# cannot show. 1 unit = 1 inch, so figsize must track the ylim span.
fig, ax = plt.subplots(figsize=(12, 5.6), dpi=200)
ax.set_xlim(0, 12)
ax.set_ylim(0.35, 5.95)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)


def box(x, y, w, h, fill, edge=None, lw=0, z=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor=fill, edgecolor=edge if edge else fill, linewidth=lw,
        zorder=z))


def label(x, y, title, sub=None, sub2=None, color=TEXT, title_size=15.5,
          sub_color=GRAY, sub_size=10.5):
    ax.text(x, y, title, color=color, fontsize=title_size, fontweight="bold",
            ha="center", va="center", zorder=4)
    if sub:
        ax.text(x, y - 0.3, sub, color=sub_color, fontsize=sub_size,
                ha="center", va="center", zorder=4)
    if sub2:
        ax.text(x, y - 0.56, sub2, color=sub_color, fontsize=sub_size,
                ha="center", va="center", zorder=4)


def arrow(x1, y1, x2, y2, color, style="<|-|>", lw=2.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                mutation_scale=18, shrinkA=0, shrinkB=0),
                zorder=3)


# ----- the container -----
box(2.55, 0.62, 5.0, 5.05, PANEL_FILL, PANEL_EDGE, lw=1.6, z=1)
ax.text(5.05, 5.35, "The container", color=BLUE, fontsize=16,
        fontweight="bold", ha="center", va="center", zorder=4)
ax.text(5.05, 5.08, "one instance, one host", color=GRAY, fontsize=10.5,
        ha="center", va="center", zorder=4)

box(2.95, 4.03, 4.2, 0.85, "#ffffff", PANEL_EDGE, lw=1.2)
label(5.05, 4.58, "The app", "serves the page, holds one session per user")

box(2.95, 2.62, 4.2, 1.05, "#ffffff", PANEL_EDGE, lw=1.2)
label(5.05, 3.42, "The harness", "the Agent SDK, one subprocess per session")

box(2.95, 1.32, 2.0, 1.0, SAGE_FILL)
label(3.95, 2.03, "Built-in tools", "Bash, Read, Write", color=SAGE,
      title_size=13, sub_size=10)
ax.text(3.95, 1.52, "run here", color=SAGE, fontsize=10.5, fontweight="bold",
        ha="center", va="center", zorder=4)

box(5.15, 1.32, 2.0, 1.0, SAGE_FILL)
label(6.15, 2.03, "Tools you write", "Python functions", color=SAGE,
      title_size=13, sub_size=10)
ax.text(6.15, 1.52, "run here", color=SAGE, fontsize=10.5, fontweight="bold",
        ha="center", va="center", zorder=4)

ax.text(5.05, 0.92, "your API key lives here, as a platform secret",
        color=GRAY, fontsize=10.5, style="italic", ha="center", va="center",
        zorder=4)

# ----- browser -----
box(0.3, 4.03, 1.85, 0.85, DARK)
ax.text(1.225, 4.58, "Browser", color="white", fontsize=15.5,
        fontweight="bold", ha="center", va="center", zorder=4)

arrow(2.2, 4.45, 2.9, 4.45, BLUE)
ax.text(2.55, 4.72, "HTTPS", color=GRAY, fontsize=10, ha="center",
        va="center", zorder=4)

arrow(5.05, 4.03, 5.05, 3.72, BLUE, style="<|-|>")

# ----- services -----
box(8.35, 4.03, 3.3, 0.85, DARK)
ax.text(10.0, 4.58, "Model provider", color="white", fontsize=15.5,
        fontweight="bold", ha="center", va="center", zorder=4)
ax.text(10.0, 4.28, "OpenRouter, then Z.ai", color="#d8d5dc", fontsize=10.5,
        ha="center", va="center", zorder=4)

box(8.35, 2.50, 3.3, 1.05, PANEL_FILL, PANEL_EDGE, lw=1.4)
ax.text(10.0, 3.30, "MCP server", color=BLUE, fontsize=15.5,
        fontweight="bold", ha="center", va="center", zorder=4)
ax.text(10.0, 3.02, "someone else's machine", color=GRAY,
        fontsize=10, ha="center", va="center", zorder=4)
ax.text(10.0, 2.74, "holds its own credential", color=GRAY, fontsize=10,
        style="italic", ha="center", va="center", zorder=4)

box(8.35, 1.25, 3.3, 0.85, SAGE_FILL, SAGE, lw=1.4)
ax.text(10.0, 1.80, "Yahoo Finance", color=SAGE, fontsize=15.5,
        fontweight="bold", ha="center", va="center", zorder=4)
ax.text(10.0, 1.50, "your yfinance tool calls it", color=GRAY, fontsize=10.5,
        ha="center", va="center", zorder=4)

arrow(7.6, 3.45, 8.35, 4.15, BLUE)
arrow(7.6, 3.02, 8.35, 3.02, BLUE)
arrow(7.2, 1.80, 8.35, 1.68, SAGE)

ax.text(10.0, 0.72, "Every hop leaves the container, over HTTPS",
        color=GRAY, fontsize=11, style="italic", ha="center", va="center",
        zorder=4)

fig.savefig("slides/images/session08-where-it-runs.png", facecolor=BG)
print("saved slides/images/session08-where-it-runs.png")

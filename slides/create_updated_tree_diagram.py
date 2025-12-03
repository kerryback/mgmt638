import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import matplotlib.lines as mlines

# Create figure with white background
fig, ax = plt.subplots(1, 1, figsize=(14, 9), facecolor='white')
ax.set_xlim(0, 10)
ax.set_ylim(1.5, 10)  # Adjusted to remove bottom white space
ax.axis('off')
ax.set_facecolor('white')

# Colors - professional palette
folder_color = '#FFD966'  # Yellow for folders
md_color = '#A8D5BA'      # Soft green for markdown
py_color = '#FFB366'      # Soft orange for python
json_color = '#A2C4E0'    # Soft blue for json

# Function to draw folder
def draw_folder(ax, x, y, width, height, label, color=folder_color):
    # Main folder rectangle
    folder = Rectangle((x, y), width, height,
                       facecolor=color, edgecolor='#333333', linewidth=2)
    ax.add_patch(folder)

    # Folder tab
    tab_width = width * 0.35
    tab_height = height * 0.25
    tab = Rectangle((x, y + height), tab_width, tab_height,
                    facecolor=color, edgecolor='#333333', linewidth=2)
    ax.add_patch(tab)

    # Label
    ax.text(x + width/2, y + height/2, label,
            ha='center', va='center', fontsize=10, fontweight='bold',
            family='sans-serif')

# Function to draw file
def draw_file(ax, x, y, width, height, label, color=md_color):
    # File rectangle
    file_rect = Rectangle((x, y), width, height,
                          facecolor=color, edgecolor='#555555', linewidth=1.5)
    ax.add_patch(file_rect)

    # Small corner fold effect
    fold_size = min(width, height) * 0.15
    fold_points = [
        [x + width, y + height],
        [x + width - fold_size, y + height],
        [x + width, y + height - fold_size]
    ]
    fold = mpatches.Polygon(fold_points, facecolor='white',
                           edgecolor='#555555', linewidth=1.5)
    ax.add_patch(fold)

    # Label
    ax.text(x + width/2, y + height/2, label,
            ha='center', va='center', fontsize=8.5, family='monospace')

# Function to draw connecting line
def draw_line(ax, x1, y1, x2, y2):
    line = mlines.Line2D([x1, x2], [y1, y2], color='#888888',
                        linewidth=2, linestyle='-', alpha=0.7)
    ax.add_line(line)

# Title removed per user request

# Root folder
draw_folder(ax, 3.5, 8.5, 3, 0.6, '.claude')
root_x, root_y = 5, 8.5

# Level 1 - Direct children
# CLAUDE.md
draw_file(ax, 1.0, 7.2, 2.0, 0.5, 'CLAUDE.md', md_color)
draw_line(ax, root_x, root_y, 2.0, 7.7)

# settings.local.json
draw_file(ax, 3.5, 7.2, 2.5, 0.5, 'settings.local.json', json_color)
draw_line(ax, root_x, root_y, 4.75, 7.7)

# skills folder
draw_folder(ax, 6.5, 7.2, 2.0, 0.5, 'skills')
draw_line(ax, root_x, root_y, 7.5, 7.7)

skills_x, skills_y = 7.5, 7.2

# Level 2 - Inside skills/ - references, monthly-analysis, and weekly-analysis
# references folder
draw_folder(ax, 0.5, 5.8, 1.8, 0.5, 'references')
draw_line(ax, skills_x, skills_y, 1.4, 6.3)

# monthly-analysis folder
draw_folder(ax, 2.8, 5.8, 2.5, 0.5, 'monthly-analysis')
draw_line(ax, skills_x, skills_y, 4.05, 6.3)

# weekly-analysis folder
draw_folder(ax, 5.8, 5.8, 2.3, 0.5, 'weekly-analysis')
draw_line(ax, skills_x, skills_y, 6.95, 6.3)

# Level 3 - Inside references/
ref_x, ref_y = 1.4, 5.8

# rice_database_schema.md
draw_file(ax, 0.2, 4.7, 2.4, 0.4, 'rice_database_schema.md', md_color)
draw_line(ax, ref_x, ref_y, 1.4, 5.1)

# scripts folder in references
draw_folder(ax, 0.5, 4.1, 1.8, 0.4, 'scripts')
draw_line(ax, ref_x, ref_y, 1.4, 4.5)

# Inside references/scripts/
ref_scripts_x, ref_scripts_y = 1.4, 4.1
y_pos = 3.2
ref_files = [
    'check_precomputed.py',
    'precomputed_variables.py'
]
for i, filename in enumerate(ref_files):
    y = y_pos - i * 0.55
    draw_file(ax, 0.3, y, 2.2, 0.4, filename, py_color)
    draw_line(ax, ref_scripts_x, ref_scripts_y, 1.4, y + 0.2)

# Level 3 - Inside monthly-analysis/
monthly_x, monthly_y = 4.05, 5.8

# SKILL.md
draw_file(ax, 3.0, 4.7, 1.6, 0.4, 'SKILL.md', md_color)
draw_line(ax, monthly_x, monthly_y, 3.8, 5.1)

# scripts folder
draw_folder(ax, 4.3, 4.7, 1.5, 0.4, 'scripts')
draw_line(ax, monthly_x, monthly_y, 5.05, 5.1)

# Inside monthly-analysis/scripts/
monthly_scripts_x, monthly_scripts_y = 5.05, 4.7
y_pos = 3.8
files = [
    'fetch_monthly_data.py',
    'merge_monthly_fund...py'
]
for i, filename in enumerate(files):
    y = y_pos - i * 0.55
    draw_file(ax, 3.5, y, 2.8, 0.4, filename, py_color)
    draw_line(ax, monthly_scripts_x, monthly_scripts_y, 4.9, y + 0.2)

# Level 3 - Inside weekly-analysis/
weekly_x, weekly_y = 6.95, 5.8

# SKILL.md
draw_file(ax, 6.0, 4.7, 1.6, 0.4, 'SKILL.md', md_color)
draw_line(ax, weekly_x, weekly_y, 6.8, 5.1)

# scripts folder
draw_folder(ax, 7.3, 4.7, 1.5, 0.4, 'scripts')
draw_line(ax, weekly_x, weekly_y, 8.05, 5.1)

# Inside weekly-analysis/scripts/
weekly_scripts_x, weekly_scripts_y = 8.05, 4.7
y_pos = 3.8
files_weekly = [
    'fetch_weekly_data.py',
    'merge_weekly_fund...py'
]
for i, filename in enumerate(files_weekly):
    y = y_pos - i * 0.55
    draw_file(ax, 6.5, y, 2.6, 0.4, filename, py_color)
    draw_line(ax, weekly_scripts_x, weekly_scripts_y, 7.8, y + 0.2)

# Legend and notes removed per user request

plt.tight_layout()
plt.savefig('slides/claude_skills_structure.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("Directory structure diagram updated: slides/claude_skills_structure.png")
plt.close()

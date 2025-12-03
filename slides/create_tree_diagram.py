import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import matplotlib.lines as mlines

# Create figure with white background
fig, ax = plt.subplots(1, 1, figsize=(14, 11), facecolor='white')
ax.set_xlim(0, 10)
ax.set_ylim(0, 13)
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

    # Label with folder icon
    ax.text(x + width/2, y + height/2, '📁 ' + label,
            ha='center', va='center', fontsize=11, fontweight='bold',
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
            ha='center', va='center', fontsize=9, family='monospace')

# Function to draw connecting line
def draw_line(ax, x1, y1, x2, y2):
    line = mlines.Line2D([x1, x2], [y1, y2], color='#888888',
                        linewidth=2, linestyle='-', alpha=0.7)
    ax.add_line(line)

# Title
ax.text(5, 12.5, 'Claude Skills: .claude Folder Structure',
        ha='center', va='top', fontsize=20, fontweight='bold',
        family='sans-serif', color='#2C3E50')

# Root folder
draw_folder(ax, 3.8, 11.2, 2.4, 0.6, '.claude')

# Level 1 - Direct children
root_x, root_y = 5, 11.2

# CLAUDE.md
draw_file(ax, 0.3, 9.8, 2, 0.5, 'CLAUDE.md', md_color)
draw_line(ax, root_x, root_y, 1.3, 10.3)

# settings.local.json
draw_file(ax, 2.5, 9.8, 2.3, 0.5, 'settings.local.json', json_color)
draw_line(ax, root_x, root_y, 3.65, 10.3)

# skills folder
draw_folder(ax, 7, 9.8, 1.8, 0.5, 'skills')
draw_line(ax, root_x, root_y, 7.9, 10.3)

skills_x, skills_y = 7.9, 9.8

# Level 2 - Inside skills/
# AUTOMATIC_VARIABLES_UPDATE.md
draw_file(ax, 6.2, 8.4, 3.2, 0.45, 'AUTO...UPDATE.md', md_color)
draw_line(ax, skills_x, skills_y, 7.8, 8.85)

# monthly-analysis folder
draw_folder(ax, 0.5, 7.5, 2.3, 0.5, 'monthly-analysis')
draw_line(ax, skills_x, skills_y, 1.65, 8)

# weekly-analysis folder
draw_folder(ax, 3.5, 7.5, 2.1, 0.5, 'weekly-analysis')
draw_line(ax, skills_x, skills_y, 4.55, 8)

# xlsx folder
draw_folder(ax, 6.3, 7.5, 1.5, 0.5, 'xlsx')
draw_line(ax, skills_x, skills_y, 7.05, 8)

# Level 3 - Inside monthly-analysis/
monthly_x, monthly_y = 1.65, 7.5
y_pos = 6.3
files_monthly = [
    ('check_precomputed.py', py_color),
    ('fetch_monthly_data.py', py_color),
    ('merge_monthly_...py', py_color),
    ('precomputed_var...py', py_color),
    ('README.md', md_color),
    ('schema_cache.json', json_color),
    ('SKILL.md', md_color)
]

for i, (filename, color) in enumerate(files_monthly):
    y = y_pos - i * 0.58
    draw_file(ax, 0.1, y, 2.3, 0.4, filename, color)
    draw_line(ax, monthly_x, monthly_y, 1.25, y + 0.2)

# Level 3 - Inside weekly-analysis/
weekly_x, weekly_y = 4.55, 7.5
y_pos = 6.3
files_weekly = [
    ('fetch_weekly_data.py', py_color),
    ('merge_weekly_fu...py', py_color),
    ('README.md', md_color),
    ('SKILL.md', md_color)
]

for i, (filename, color) in enumerate(files_weekly):
    y = y_pos - i * 0.58
    draw_file(ax, 3.3, y, 2.3, 0.4, filename, color)
    draw_line(ax, weekly_x, weekly_y, 4.45, y + 0.2)

# Level 3 - Inside xlsx/
draw_file(ax, 6.1, 6.3, 1.6, 0.4, 'SKILL.md', md_color)
draw_line(ax, 7.05, 7.5, 6.9, 6.5)

# Legend
legend_y = 1.2
legend_box = Rectangle((0.2, 0.2), 3.5, 1.5,
                       facecolor='#F8F9FA', edgecolor='#333333',
                       linewidth=2, alpha=0.9)
ax.add_patch(legend_box)

ax.text(0.4, legend_y + 0.3, 'File Types:', fontsize=11,
        fontweight='bold', family='sans-serif')

legend_items = [
    (folder_color, '📁 Folders'),
    (md_color, '📄 Markdown (.md)'),
    (py_color, '🐍 Python (.py)'),
    (json_color, '📋 JSON (.json)')
]

for i, (color, label) in enumerate(legend_items):
    rect = Rectangle((0.5, legend_y - 0.2 - i*0.35), 0.35, 0.25,
                     facecolor=color, edgecolor='#555555', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(1.0, legend_y - 0.075 - i*0.35, label,
            ha='left', va='center', fontsize=9, family='sans-serif')

# Add informative note
note_box = Rectangle((4, 0.2), 5.8, 1.5,
                     facecolor='#FFF8DC', edgecolor='#333333',
                     linewidth=2, alpha=0.9)
ax.add_patch(note_box)

note_title = "Key Points:"
ax.text(4.2, legend_y + 0.3, note_title, fontsize=11,
        fontweight='bold', family='sans-serif', ha='left')

notes = [
    "• Each skill is a self-contained module",
    "• SKILL.md defines the skill interface",
    "• Python scripts implement functionality",
    "• Skills can be project-specific or user-global"
]

for i, note in enumerate(notes):
    ax.text(4.3, legend_y - 0.15 - i*0.32, note,
            fontsize=8.5, family='sans-serif', ha='left', va='top')

plt.tight_layout()
plt.savefig('slides/claude_skills_structure.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("Directory structure diagram created: slides/claude_skills_structure.png")
plt.close()

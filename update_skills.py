#!/usr/bin/env python3
"""
Update the skills/ distribution folder from .claude/skills/

This script copies skills from the working .claude/skills/ directory
to the skills/ distribution folder that gets published to the website.
"""

import shutil
from pathlib import Path

# Define source and destination
CLAUDE_SKILLS = Path('.claude/skills')
DIST_SKILLS = Path('skills')

# Skills to distribute (folders to copy)
SKILLS_TO_DISTRIBUTE = [
    'rice-data-query',
    'momentum-calculator'
]

def update_skills():
    """Copy skills from .claude/skills/ to skills/ for distribution."""

    print("Updating skills distribution folder...")

    for skill_name in SKILLS_TO_DISTRIBUTE:
        source = CLAUDE_SKILLS / skill_name
        dest = DIST_SKILLS / skill_name

        if not source.exists():
            print(f"Warning: {source} does not exist, skipping...")
            continue

        # Create destination directory if it doesn't exist
        dest.mkdir(parents=True, exist_ok=True)

        # Files to copy for each skill
        files_to_copy = ['SKILL.md', 'README.md']

        # Add calculate_momentum.py for momentum-calculator skill
        if skill_name == 'momentum-calculator':
            files_to_copy.append('calculate_momentum.py')

        # Copy each file
        for filename in files_to_copy:
            source_file = source / filename
            dest_file = dest / filename

            if source_file.exists():
                shutil.copy2(source_file, dest_file)
                print(f"  Copied: {skill_name}/{filename}")
            else:
                print(f"  Warning: {source_file} not found, skipping...")

    print("\nSkills distribution folder updated successfully!")
    print("Files are ready to be published to docs/skills/ when you run 'quarto render'")

if __name__ == '__main__':
    update_skills()

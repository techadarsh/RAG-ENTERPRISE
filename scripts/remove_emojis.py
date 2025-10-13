#!/usr/bin/env python3
"""
Remove emojis from codebase
- In .md files: Replace  with [x], remove other emojis
- In other files: Remove all emojis
"""

import re
import os
from pathlib import Path

# Common emojis to remove
EMOJI_PATTERN = re.compile(
    r'[\U0001F300-\U0001F9FF]|'  # Miscellaneous Symbols and Pictographs
    r'[\U0001F600-\U0001F64F]|'  # Emoticons
    r'[\U0001F680-\U0001F6FF]|'  # Transport and Map Symbols
    r'[\U0001F1E0-\U0001F1FF]|'  # Flags
    r'[\U00002600-\U000027BF]|'  # Miscellaneous Symbols
    r'[\U0001F900-\U0001F9FF]|'  # Supplemental Symbols and Pictographs
    r'[\U00002700-\U000027BF]|'  # Dingbats
    r'[]'
)

# Specific checkmark emojis to replace with [x] in markdown
CHECKMARK_PATTERN = re.compile(r'')

# Files/directories to skip
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.pytest_cache', 'venv', 'env'}
SKIP_FILES = {'package-lock.json', 'bun.lockb', '.DS_Store'}

# File extensions to process
EXTENSIONS = {'.py', '.md', '.js', '.jsx', '.ts', '.tsx', '.sh', '.txt', '.yml', '.yaml', '.json', '.env', '.example'}

def should_process(file_path):
    """Check if file should be processed"""
    path = Path(file_path)
    
    # Skip if in skip directories
    for part in path.parts:
        if part in SKIP_DIRS:
            return False
    
    # Skip specific files
    if path.name in SKIP_FILES:
        return False
    
    # Check extension
    return path.suffix in EXTENSIONS or path.name.startswith('.env')

def clean_content(content, is_markdown=False):
    """Remove emojis from content"""
    if is_markdown:
        # First replace  with [x]
        content = CHECKMARK_PATTERN.sub('[x]', content)
    
    # Remove all other emojis
    content = EMOJI_PATTERN.sub('', content)
    
    return content

def process_file(file_path):
    """Process a single file"""
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        # Clean content
        is_markdown = file_path.endswith('.md')
        cleaned_content = clean_content(original_content, is_markdown)
        
        # Write back if changed
        if cleaned_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            return True, file_path
        
        return False, None
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, None

def main():
    """Main function"""
    root_dir = Path(__file__).parent.parent
    modified_files = []
    
    print(f"Scanning {root_dir}...")
    print("=" * 60)
    
    # Walk through all files
    for root, dirs, files in os.walk(root_dir):
        # Remove skip directories from traversal
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            if should_process(file_path):
                changed, path = process_file(file_path)
                if changed:
                    rel_path = os.path.relpath(path, root_dir)
                    modified_files.append(rel_path)
                    print(f"[MODIFIED] {rel_path}")
    
    print("=" * 60)
    print(f"\nTotal files modified: {len(modified_files)}")
    
    if modified_files:
        print("\nModified files:")
        for f in sorted(modified_files):
            print(f"  - {f}")

if __name__ == '__main__':
    main()

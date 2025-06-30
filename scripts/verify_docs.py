#!/usr/bin/env python3
"""
Script to verify that all documentation files are properly linked in the documentation structure.
"""
import os
import re
from pathlib import Path
from typing import List, Set, Dict

# Configuration
ROOT_DIR = Path(__file__).parent.parent
DOCS_DIR = ROOT_DIR / "docs"
MAIN_DOCS = ["README.md", "DOCS.md"]

# Track all markdown files and their references
markdown_files: Set[Path] = set()
file_references: Dict[Path, List[Path]] = {}

def find_markdown_files(directory: Path) -> None:
    """Find all markdown files in the directory tree."""
    for path in directory.rglob("*.md"):
        if "node_modules" not in str(path):
            markdown_files.add(path.relative_to(ROOT_DIR))

def find_links_in_file(file_path: Path) -> Set[str]:
    """Find all markdown links in a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return set()
        
    # Find markdown links [text](url)
    links = set(re.findall(r'\[.*?\]\((.*?)\)', content))
    # Find relative paths in markdown links
    return {link for link in links if link.endswith('.md') and not link.startswith('http')}

def verify_links() -> None:
    """Verify that all markdown files are referenced."""
    # Track which files reference which other files
    for file_path in markdown_files:
        abs_path = ROOT_DIR / file_path
        links = find_links_in_file(abs_path)
        
        for link in links:
            # Resolve relative paths
            if link.startswith('/'):
                target = ROOT_DIR / link[1:]
            else:
                target = (abs_path.parent / link).resolve()
            
            try:
                rel_path = target.relative_to(ROOT_DIR)
                if rel_path in markdown_files:
                    if rel_path not in file_references:
                        file_references[rel_path] = []
                    file_references[rel_path].append(file_path)
            except ValueError:
                # Path not relative to root, skip
                pass
    
    # Find unreferenced files (except for MAIN_DOCS and files in node_modules)
    unreferenced = []
    for file_path in markdown_files:
        if (file_path.name in MAIN_DOCS or 
            str(file_path).startswith('frontend/node_modules/') or
            file_path.name == 'CHANGELOG.md' or 
            file_path.name == 'HISTORY.md'):
            continue
            
        if file_path not in file_references:
            unreferenced.append(file_path)
    
    # Print results
    if unreferenced:
        print("\n⚠️  The following documentation files are not referenced by any other documentation:")
        for path in sorted(unreferenced):
            print(f"  - {path}")
        
        print("\nConsider adding references to these files in the appropriate documentation.")
    else:
        print("✅ All documentation files are properly referenced!")
    
    # Print reference count for each file (for debugging)
    if file_references:
        print("\nReference counts:")
        for path, refs in sorted(file_references.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  - {path}: {len(refs)} references")

def main():
    print("🔍 Scanning for documentation files...")
    find_markdown_files(ROOT_DIR)
    print(f"Found {len(markdown_files)} markdown files.")
    
    print("\n🔗 Verifying documentation links...")
    verify_links()

if __name__ == "__main__":
    main()

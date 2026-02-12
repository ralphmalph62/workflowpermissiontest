#!/usr/bin/env python3
"""
Unified translation check and comment formatter.
Used by both check-translations.yml and update-translation-status.yml workflows.

Usage: python check-and-format-translations.py <changed_files.txt> [output_dir]
Outputs:
  - comment_body.md: The formatted comment
  - has_missing: Boolean flag (true/false)
"""

import sys
import re
from collections import defaultdict
from pathlib import Path


def parse_changed_files(filepath):
    """Parse changed files from a text file."""
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def detect_missing_translations(changed_files):
    """
    Detect missing translations from changed files.
    
    Returns:
        auto_missing: list of (source_lang, target_lang, rel_path) with valid source
        manual_missing: list of target langs without valid source
    """
    # Group files by relative path
    files_by_path = defaultdict(set)
    
    for file in changed_files:
        match = re.match(r'^docs/(en|zh|ja)/(.+)$', file)
        if match:
            lang = match.group(1)
            rel_path = match.group(2)
            files_by_path[rel_path].add(lang)
    
    auto_missing = []
    manual_missing = defaultdict(set)  # rel_path -> set of missing langs
    
    for rel_path, langs in files_by_path.items():
        has_en = 'en' in langs
        has_zh = 'zh' in langs
        has_ja = 'ja' in langs
        
        # English - needs Chinese as source
        if not has_en:
            if has_zh:
                auto_missing.append(('zh', 'en', rel_path))
            else:
                manual_missing[rel_path].add('en')
        
        # Chinese - needs English as source
        if not has_zh:
            if has_en:
                auto_missing.append(('en', 'zh', rel_path))
            else:
                manual_missing[rel_path].add('zh')
        
        # Japanese - needs English as source
        if not has_ja:
            if has_en:
                auto_missing.append(('en', 'ja', rel_path))
            else:
                manual_missing[rel_path].add('ja')
    
    return auto_missing, manual_missing


def format_comment_body(auto_missing, manual_missing):
    """Format the GitHub comment body."""
    lines = [
        "<!-- translation-check-comment -->",
        "## 🌍 Translation Check",
        "",
        "This PR contains documentation changes that are missing translations in some languages.",
        "",
    ]
    
    # Auto-translatable section
    if auto_missing:
        lines.extend([
            "### Missing Translations (Can be auto-generated)",
            "",
            "Please check the boxes below for the translations you would like to request. A docs maintainer can trigger automatic translation by commenting `/translate` on this PR.",
            "",
        ])
        for source_lang, target_lang, rel_path in auto_missing:
            lines.append(f"- [ ] {source_lang} {target_lang} {rel_path}")
        lines.append("")
    
    # Manual-only section
    if manual_missing:
        lines.extend([
            "### Missing Translations (Require manual translation by a member of docs-maintainer)",
            "",
        ])
        for rel_path in sorted(manual_missing.keys()):
            for lang in sorted(manual_missing[rel_path]):
                lines.append(f"- {lang}/{rel_path}")
        lines.extend([
            "",
            "⚠️ **Note:** These translations cannot be auto-generated because the required source file does not exist in this PR. Please add the source file to enable automatic translation:",
            "",
            "- **English** (`en/...`) can be the source for translation to Chinese and Japanese.",
            "- **Chinese** (`zh/...`) can be the source for translation to English.",
            "- Japanese can never be a source file.",
        ])
    
    lines.extend([
        "",
        "---",
        "*If you've already added these translations manually, please disregard this message. The check will update automatically.*",
    ])
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python check-and-format-translations.py <changed_files.txt> [output_dir]")
        sys.exit(1)
    
    changed_files_path = sys.argv[1]
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse changed files
    changed_files = parse_changed_files(changed_files_path)
    if not changed_files:
        print("No files to process")
        output_dir.joinpath("has_missing").write_text("false")
        return
    
    # Detect missing translations
    auto_missing, manual_missing = detect_missing_translations(changed_files)
    
    has_missing = bool(auto_missing or manual_missing)
    
    # Output results
    output_dir.joinpath("has_missing").write_text("true" if has_missing else "false")
    
    if has_missing:
        comment_body = format_comment_body(auto_missing, manual_missing)
        output_dir.joinpath("comment_body.md").write_text(comment_body)
        print(f"Comment body written to {output_dir}/comment_body.md")
    else:
        print("No missing translations found")
    
    print(f"has_missing={str(has_missing).lower()}")


if __name__ == "__main__":
    main()

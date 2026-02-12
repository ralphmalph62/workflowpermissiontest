#!/usr/bin/env python3
"""
Script to find missing translations for documentation files.
Usage: python find-missing-translations.py <changed_files.txt> [output_file]
"""

import sys
from collections import defaultdict
from pathlib import Path


def find_missing_translations(changed_files_path, output_path=None):
    """
    Find missing translations for changed documentation files.
    
    Args:
        changed_files_path: Path to file containing list of changed files
        output_path: Optional path to write missing translations
        
    Returns:
        List of tuples (source_lang, target_lang, source_file)
    """
    # Read changed files
    with open(changed_files_path, 'r') as f:
        changed_files = [line.strip() for line in f if line.strip()]
    
    if not changed_files:
        print("No files to process")
        return []
    
    # Group by relative path
    files_by_path = defaultdict(set)
    
    for file in changed_files:
        parts = file.split('/', 2)
        if len(parts) == 3 and parts[0] == 'docs' and parts[1] in ['en', 'zh', 'ja']:
            lang = parts[1]
            rel_path = parts[2]
            files_by_path[rel_path].add(lang)
    
    # Find missing translations with proper source language selection
    # Rules:
    # - English and Chinese are the only source languages permitted
    # - English can translate to Japanese or Chinese
    # - Chinese can only translate to English
    # - Japanese files are never source files
    missing = []
    
    for rel_path, langs in files_by_path.items():
        # For each file, check which languages are missing
        for target_lang in ['en', 'zh', 'ja']:
            if target_lang not in langs:
                # Determine the appropriate source language
                source_lang = None
                
                if target_lang == 'en':
                    # For English target: use Chinese as source
                    if 'zh' in langs:
                        source_lang = 'zh'
                elif target_lang == 'zh':
                    # For Chinese target: use English as source
                    if 'en' in langs:
                        source_lang = 'en'
                elif target_lang == 'ja':
                    # For Japanese target: use English as source
                    if 'en' in langs:
                        source_lang = 'en'
                
                # Add to missing list if we found a valid source
                if source_lang:
                    source_file = f"docs/{source_lang}/{rel_path}"
                    missing.append((source_lang, target_lang, source_file))
    
    if missing:
        print(f"Found {len(missing)} missing translations:")
        for source_lang, target_lang, source_file in missing:
            print(f"  {source_file} ({source_lang}) -> docs/{target_lang}/{source_file.split('/', 2)[2]}")
    else:
        print("No missing translations found")
    
    # Write to output file if specified
    if output_path and missing:
        with open(output_path, 'w') as f:
            for source_lang, target_lang, source_file in missing:
                f.write(f"{source_lang}:{target_lang}:{source_file}\n")
        print(f"\nMissing translations written to {output_path}")
    
    return missing


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find-missing-translations.py <changed_files.txt> [output_file]")
        sys.exit(1)
    
    changed_files_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    missing = find_missing_translations(changed_files_path, output_path)
    
    # Exit with status code indicating if translations are missing
    sys.exit(0 if not missing else 1)

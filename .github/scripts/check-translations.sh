#!/bin/bash

# Script to check translation completeness across docs/en, docs/zh, and docs/ja
# Usage: ./check-translations.sh <base_sha> <head_sha>

set -e

BASE_SHA="$1"
HEAD_SHA="$2"

if [ -z "$BASE_SHA" ] || [ -z "$HEAD_SHA" ]; then
  echo "Usage: $0 <base_sha> <head_sha>"
  exit 1
fi

# Get list of changed files in docs directories
git diff --name-only "$BASE_SHA" "$HEAD_SHA" | grep -E '^docs/(en|zh|ja)/' > changed_files.txt || true

if [ ! -s changed_files.txt ]; then
  echo "No documentation files changed"
  echo "HAS_CHANGES=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

echo "Documentation files changed:"
cat changed_files.txt
echo "HAS_CHANGES=true" >> "$GITHUB_OUTPUT"

# Read changed files
mapfile -t changed_files < changed_files.txt

# Arrays to track missing translations
declare -A files_by_path

# Process each changed file
for file in "${changed_files[@]}"; do
  # Extract language and relative path
  if [[ $file =~ ^docs/(en|zh|ja)/(.+)$ ]]; then
    lang="${BASH_REMATCH[1]}"
    rel_path="${BASH_REMATCH[2]}"
    
    # Track this file's relative path
    if [ -z "${files_by_path[$rel_path]}" ]; then
      files_by_path[$rel_path]="$lang"
    else
      files_by_path[$rel_path]="${files_by_path[$rel_path]},$lang"
    fi
  fi
done

# Check which files are missing translations
missing_translations=""
manual_only_translations=""

for rel_path in "${!files_by_path[@]}"; do
  langs="${files_by_path[$rel_path]}"
  
  # Check which languages are present
  has_en=false
  has_zh=false
  has_ja=false
  
  IFS=',' read -ra lang_array <<< "$langs"
  for lang in "${lang_array[@]}"; do
    case $lang in
      en) has_en=true ;;
      zh) has_zh=true ;;
      ja) has_ja=true ;;
    esac
  done
  
  # Build list of missing translations
  # Categorize based on whether auto-translation is possible
  auto_missing=""
  manual_missing=""
  
  if [ "$has_en" = true ] || [ "$has_zh" = true ] || [ "$has_ja" = true ]; then
    # Check English - needs Chinese as source
    if [ "$has_en" = false ]; then
      if [ "$has_zh" = true ]; then
        auto_missing="${auto_missing}- [ ] \`docs/en/$rel_path\`%0A"
      else
        manual_missing="${manual_missing}- [ ] \`docs/en/$rel_path\`%0A"
      fi
    fi
    
    # Check Chinese - needs English as source
    if [ "$has_zh" = false ]; then
      if [ "$has_en" = true ]; then
        auto_missing="${auto_missing}- [ ] \`docs/zh/$rel_path\`%0A"
      else
        manual_missing="${manual_missing}- [ ] \`docs/zh/$rel_path\`%0A"
      fi
    fi
    
    # Check Japanese - needs English as source
    if [ "$has_ja" = false ]; then
      if [ "$has_en" = true ]; then
        auto_missing="${auto_missing}- [ ] \`docs/ja/$rel_path\`%0A"
      else
        manual_missing="${manual_missing}- [ ] \`docs/ja/$rel_path\`%0A"
      fi
    fi
  fi
  
  if [ -n "$auto_missing" ]; then
    missing_translations="${missing_translations}%0A**File: \`$rel_path\`**%0A${auto_missing}"
  fi
  
  if [ -n "$manual_missing" ]; then
    manual_only_translations="${manual_only_translations}%0A**File: \`$rel_path\`**%0A${manual_missing}"
  fi
done

if [ -n "$missing_translations" ] || [ -n "$manual_only_translations" ]; then
  echo "HAS_MISSING=true" >> "$GITHUB_OUTPUT"
  # Save to files for use in GitHub Actions
  echo "$missing_translations" > missing_translations.txt
  echo "$manual_only_translations" > manual_translations.txt
  echo "Missing translations categorized and saved"
else
  echo "HAS_MISSING=false" >> "$GITHUB_OUTPUT"
  echo "All translations are complete!"
fi

# Translation Checkbox Selection Fix

## Problem

The `/translate` command was generating translations for ALL missing files instead of only those with checked boxes. 

**Example from PR #123:**
- User checked only the `dict_mapping.md` (ZH→EN) checkbox
- Workflow translated BOTH `dict_mapping.md` AND `Etl_in_loading.md` (all missing translations)

## Root Cause

The `translate-command.yml` workflow's "Get files needing translation" step:
1. Calculated all missing translations from `git diff`
2. Did not parse the translation check comment to see which boxes were checked
3. Generated translations for everything with a valid source file

## Solution

Modified the `translate-command.yml` workflow to:

1. **Fetch PR comments** using GitHub API
2. **Find the translation check comment** (posted by github-actions[bot] containing "Missing translations detected")
3. **Parse checkbox states** - look for `- [x]` vs `- [ ]`
4. **Extract translation details** from checked boxes:
   - Source language (EN, ZH, JA)
   - Target language (EN, ZH, JA)
   - File path
5. **Only translate checked files**

## Changes Made

### `translate-command.yml`

**Before:**
- Step: "Get files needing translation"
- Logic: Analyzed git diff → generated list of ALL missing translations

**After:**
- Step: "Get checked translations from comment"
- Logic: Fetch PR comments → find translation check comment → parse checked boxes → generate list of ONLY checked translations

### New Behavior

When `/translate` is run:
- ✅ Only files with `- [x]` checked boxes are translated
- ✅ Files with `- [ ]` unchecked boxes are skipped
- ✅ If no boxes are checked, workflow comments: "No translations selected"

### Python Script Logic

```python
# Find checked boxes in comment
for line in translation_comment.split('\n'):
    # Look for: - [x] **EN → ZH**: `loading/file.md`
    if re.match(r'^\s*-\s*\[[xX]\]', line):
        # Extract source lang, target lang, file path
        match = re.search(r'\*\*(EN|ZH|JA)\s*→\s*(EN|ZH|JA)\*\*:\s*`([^`]+)`', line)
        if match:
            source_lang = match.group(1).lower()
            target_lang = match.group(2).lower()
            rel_path = match.group(3)
            # Add to translation list
```

## Testing

### Manual Test Scenario

1. Create PR with changes to `docs/en/test1.md` and `docs/en/test2.md`
2. Wait for translation check comment with 4 checkboxes:
   - [ ] EN → ZH: test1.md
   - [ ] EN → JA: test1.md
   - [ ] EN → ZH: test2.md
   - [ ] EN → JA: test2.md
3. Check only ONE box: `[x] EN → ZH: test1.md`
4. Comment `/translate`
5. **Expected:** Only `docs/zh/test1.md` is created
6. **Previous behavior:** All 4 translations would be created

### Edge Cases Handled

- **No checkboxes selected**: Comment warns user to select translations
- **Partial selection**: Only selected translations are generated
- **Case insensitive**: Accepts both `[x]` and `[X]`
- **Missing comment**: Gracefully exits if translation comment not found

## Documentation Updates

Updated [.github/workflows/README.md](.github/workflows/README.md):
- Added "How to use" section explaining checkbox selection
- Updated typical workflow to include checkbox selection step
- Clarified that only checked translations are generated

## Impact

- **User Experience**: Users now have full control over which translations to generate
- **Efficiency**: Avoids generating unwanted translations
- **Cost**: Reduces API calls to Google Gemini for translations
- **Workflow**: More flexible - can translate files incrementally

## Migration Notes

For existing PRs:
1. The translation check comment already has checkboxes
2. Users should check desired boxes before running `/translate`
3. No action needed for PRs without translation comments

## Related Files

- `.github/workflows/translate-command.yml` - Main fix
- `.github/workflows/README.md` - Documentation update
- `CHECKBOX_FIX.md` - This document

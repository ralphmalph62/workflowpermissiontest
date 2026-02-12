# Comment Format Fix - PR #124 Resolution

## Problem

When PR #124 was created with changes to multiple language files across different commits, the translation check comment was not updating properly with the new checkbox format. Specifically:
- **Commit 1**: Changed `docs/ja/introduction/Architecture.md`
  - Expected: Comment showing auto-translatable options
- **Commit 2**: Changed `docs/zh/introduction/Architecture.md`
  - Expected: Comment to be updated with new **ZH → EN** checkbox
  - Actual: Comment was not replaced and didn't show ZH → EN option

## Root Cause

The `check-translations.yml` and `translate-command.yml` workflows were using incompatible comment formats:

### Old Format (check-translations.yml):
```markdown
- [ ] `docs/en/file.md`
```

### Expected Format (translate-command.yml):
```markdown
- [ ] **SOURCE → TARGET**: `relative/path.md` *(auto-generated)*
```

The translate-command parser was looking for language pair format like `**EN → ZH**` but the comment was only showing file full paths without language direction.

## Solution

### 1. Updated check-translations.yml

Changed the checkbox generation to include proper language pair format with relative paths:

**Before:**
```bash
auto_missing="${auto_missing}- [ ] \`docs/en/$rel_path\`%0A"
```

**After:**
```bash
auto_missing="${auto_missing}- [ ] **EN → ZH**: \`$rel_path\` *(auto-generated)*%0A"
# For Chinese source:
auto_missing="${auto_missing}- [ ] **ZH → EN**: \`$rel_path\` *(auto-generated)*%0A"
# etc.
```

### 2. Improved translate-command.yml

Made comment search more flexible to find translation check comments:

**Before:**
```python
if (comment['user']['login'] == 'github-actions[bot]' and 
    'Missing translations detected' in comment['body']):
```

**After:**
```python
if (comment['user']['login'] == 'github-actions[bot]' and 
    ('Missing translations' in comment['body'] or 'Translation Check' in comment['body'])):
```

## Verification

After fixes, PR #124's comment now correctly shows:

```markdown
## 🌍 Translation Check

This PR contains documentation changes that are missing translations in some languages.

### Missing Translations (Can be auto-generated)

Please check the boxes below for the translations you would like to request...

**File: `introduction/Architecture.md`**
- [ ] **ZH → EN**: `introduction/Architecture.md` *(auto-generated)*
```

This shows that:
1. Japanese file change detected ✅
2. Chinese file change detected ✅
3. Comment properly formatted with `**ZH → EN**` format ✅
4. Relative file path without `docs/` prefix ✅
5. Parser can now extract:
   - Source language: `zh`
   - Target language: `en`
   - File: `introduction/Architecture.md`

## Files Modified

- `.github/workflows/check-translations.yml`: Updated checkbox format generation
- `.github/workflows/translate-command.yml`: Improved comment detection
- `.github/workflows/README.md`: Updated documentation

## Testing

When `/translate` command is now used:
1. Comment is fetched from PR
2. Parser finds all `[x]` (checked) boxes
3. Extracts source → target language pairs and file paths
4. Only translates the checked items
5. Respects user's selection rather than translating everything

## Impact

- ✅ Comments now show proper source → target language arrows
- ✅ File paths are relative and more readable
- ✅ `/translate` command can properly parse which translations user wants
- ✅ Comment updates correctly as new changes are pushed to PR
- ✅ Users have full control over which translations to request

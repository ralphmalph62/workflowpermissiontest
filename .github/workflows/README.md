# GitHub Workflows for Translation Management

This directory contains GitHub Actions workflows that automate the management of documentation translations across multiple languages (English, Chinese, Japanese).

## Overview

The workflows work together to:
1. Check if documentation changes include all required language translations
2. Allow maintainers to trigger automatic translations
3. Update PR status as translations are added

## Workflows

### 1. Check Translation Completeness (`check-translations.yml`)

**Triggers:** When a PR is opened, updated, or reopened with changes to `docs/en/`, `docs/zh/`, or `docs/ja/`

**What it does:**
- Analyzes all changed documentation files
- Identifies missing translations (e.g., if `docs/en/file.md` changed but not `docs/zh/file.md`)
- Categorizes missing translations into:
  - **Auto-translatable**: Can be generated via `/translate` command (has valid source file)
  - **Manual-only**: Requires manual translation (no valid source file in the PR)
- Posts a comment with separate checklists for each category
- Adds the `needs_translation` label if translations are missing
- Removes the label and updates the comment if all translations are complete

**Works with:** Both branch PRs and fork PRs

### 2. Handle Translation Command (`translate-command.yml`)

**Triggers:** When someone comments `/translate` on a PR

**What it does:**
- Verifies the commenter is a member of the `docs-maintainer` team
- Identifies which translations are missing
- Checks out the [StarRocks/markdown-translator](https://github.com/StarRocks/markdown-translator) repository
- Generates the missing translations
- Commits and pushes translations to the PR branch (for branch PRs)
- For fork PRs, creates a patch file that can be downloaded and applied
- Adds the `translations_added` label on success

**Permissions required:**
- Only members of the `docs-maintainer` GitHub team can trigger this workflow
- For fork PRs, the contributor must apply the generated patch manually

**Special handling for fork PRs:**
Since GitHub Actions cannot push directly to forks, the workflow:
- Generates translations and creates a `.patch` file
- Uploads the patch as a workflow artifact
- Comments on the PR with instructions for applying the patch

### 3. Update Translation Status (`update-translation-status.yml`)

**Triggers:** When the `translations_added` label is added to a PR

**What it does:**
- Re-checks translation completeness
- Updates the original comment:
  - Shows "✅ Translation Check Complete" if all translations are present
  - Shows updated checklist if some translations are still missing
- Manages labels:
  - Removes `needs_translation` if complete
  - Adds `needs_translation` back if still incomplete
- Removes the `translations_added` label after processing

## Scripts

### `check-translations.sh`

Bash script that analyzes changed files and identifies missing translations.

**Usage:**
```bash
./check-translations.sh <base_sha> <head_sha>
```

### `find-missing-translations.py`

Python script that parses changed files and generates a list of missing translations in a format suitable for the translation workflow.

**Usage:**
```bash
python find-missing-translations.py <changed_files.txt> [output_file]
```

**Output format:**
```
source_lang:target_lang:source_file_path
```

Example:
```
en:zh:docs/en/loading/StreamLoad.md
en:ja:docs/en/loading/StreamLoad.md
```

## Translation Source Language Rules

The workflows enforce specific rules about which languages can be used as translation sources:

### Permitted Source Languages
- **English (`en`)**: Can be used to translate to Chinese (`zh`) or Japanese (`ja`)
- **Chinese (`zh`)**: Can only be used to translate to English (`en`)
- **Japanese (`ja`)**: Never used as a source language

### Translation Logic

When the `/translate` command is triggered, the workflow:

1. **For Japanese translations**: Always uses English as the source
   - `docs/en/file.md` → `docs/ja/file.md`

2. **For Chinese translations**: Uses English as the source
   - `docs/en/file.md` → `docs/zh/file.md`

3. **For English translations**: Uses Chinese as the source
   - `docs/zh/file.md` → `docs/en/file.md`

### Why These Rules?

- **Quality**: English and Chinese documentation are maintained as primary sources
- **Consistency**: Japanese translations are always derived from English for consistency
- **Bidirectional EN-ZH**: Supports both English-to-Chinese and Chinese-to-English workflows
- **No cascading**: Prevents translation chains (e.g., EN → JA → ZH) that could degrade quality

### Example Scenario

If a PR contains changes to:
- `docs/en/feature.md` (changed)
- `docs/zh/feature.md` (missing)
- `docs/ja/feature.md` (missing)

The `/translate` command will:
1. Translate `docs/en/feature.md` → `docs/zh/feature.md` (English to Chinese)
2. Translate `docs/en/feature.md` → `docs/ja/feature.md` (English to Japanese)

If later only `docs/zh/feature.md` is updated:
- The workflow will only offer to translate `docs/zh/feature.md` → `docs/en/feature.md` (Chinese to English)
- It will NOT attempt to create Japanese from Chinese

## Labels

- **`needs_translation`**: Indicates the PR has documentation changes missing translations
- **`translations_added`**: Temporary label that triggers status update after translations are added

## Team Requirements

The workflows require a GitHub team named `docs-maintainer` in your organization. Members of this team can:
- Trigger automatic translations with `/translate` command
- Have their team membership verified via GitHub API

To create the team:
1. Go to your GitHub organization settings
2. Navigate to Teams
3. Create a new team named `docs-maintainer`
4. Add appropriate members

## Workflow Sequence

### Typical Flow for Branch PRs

1. Developer opens PR with changes to `docs/en/myfile.md`
2. **Check Translation Completeness** workflow runs:
   - Detects missing `docs/zh/myfile.md` and `docs/ja/myfile.md`
   - Posts comment with checklist
   - Adds `needs_translation` label
3. Docs maintainer comments `/translate`
4. **Handle Translation Command** workflow runs:
   - Verifies maintainer permissions
   - Generates translations using markdown-translator
   - Commits and pushes to PR branch
   - Adds `translations_added` label
5. **Update Translation Status** workflow runs:
   - Re-checks completeness
   - Updates comment to show completion
   - Removes `needs_translation` label
   - Removes `translations_added` label

### Typical Flow for Fork PRs

Same as above, except step 4:
- Workflow generates translations but cannot push to fork
- Creates a `.patch` file uploaded as artifact
- Comments on PR with instructions for contributor to download and apply patch
- Contributor applies patch and pushes to their fork
- Workflow detects changes and proceeds with status update

## Configuration

### Required Secrets

- `GITHUB_TOKEN`: Automatically provided by GitHub Actions (no configuration needed)
- `DOC_MEMBERSHIP_PAT`: Personal Access Token (classic) with `read:org` scope for checking team membership
  - Required for verifying if users are members of the `docs-maintainer` team
  - Create at: GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Add to repository: Settings → Secrets and variables → Actions → New repository secret
- `GEMINI_API_KEY`: Google Gemini API key for translation
  - Required by the markdown-translator tool to perform translations
  - Get your API key at: [Google AI Studio](https://aistudio.google.com/app/apikey)
  - Add to repository: Settings → Secrets and variables → Actions → New repository secret

### Required Permissions

The workflows use these permissions:
- `contents: read` or `write` (write needed for pushing translations)
- `pull-requests: write` (for comments and labels)

### Customization

To adjust which languages are checked, modify the language arrays in:
- [check-translations.yml](check-translations.yml) (lines checking for `en`, `zh`, `ja`)
- [translate-command.yml](translate-command.yml) (language checking logic in shell script)
- [update-translation-status.yml](update-translation-status.yml) (language checking logic)

To change the translation tool:
- Update the repository URL in `translate-command.yml`
- Modify the translation command (currently uses `node bin/cli.js translate -i <input> -l <language> -o <output>`)
- Update the `GEMINI_API_KEY` secret name if using a different AI service

## Troubleshooting

### Workflow doesn't run
- Check that PR includes changes to files in `docs/en/`, `docs/zh/`, or `docs/ja/`
- Verify workflow files are in `.github/workflows/` directory
- Check GitHub Actions tab for error messages

### Permission denied for `/translate` command
- Verify user is member of `docs-maintainer` team
- Check team name matches exactly (case-sensitive)
- Ensure `GITHUB_TOKEN` has permission to read team membership

### Translations not pushed to fork PR
- This is expected behavior for security reasons
- Download the patch file from workflow artifacts
- Apply with `git apply translations.patch`

### Labels not updating
- Check that workflows have `pull-requests: write` permission
- Verify labels exist in the repository (GitHub will create them automatically on first use)

### Translation failures
- Verify `GEMINI_API_KEY` secret is set correctly
- Check Google Gemini API quota and rate limits
- Ensure the API key has necessary permissions
- Review workflow logs for specific error messages from the translation tool

## Dependencies

### GitHub Actions
- `actions/checkout@v4`
- `actions/setup-node@v4`
- `actions/upload-artifact@v4`
- `peter-evans/find-comment@v3`

### External Repository
- [StarRocks/markdown-translator](https://github.com/StarRocks/markdown-translator) - Node.js-based translation tool powered by Google Gemini AI
  - Requires Node.js 16.0.0 or higher
  - Uses Google Gemini API for AI-powered translations
  - Preserves markdown formatting and structure

## Contributing

To modify these workflows:
1. Test changes on a feature branch first
2. Use small test PRs to verify behavior
3. Document any changes to requirements or behavior
4. Consider both branch and fork PR scenarios

# Multi-Language Documentation Translation Workflow

This repository includes an automated workflow to help manage translations for documentation across three languages: English, Chinese, and Japanese.

## 📁 Documentation Structure

Documentation is organized in three language-specific directories:
- `/docs/en/` - English documentation
- `/docs/zh/` - Chinese documentation
- `/docs/ja/` - Japanese documentation

## 🤖 Automated Translation Check

### How It Works

When you create or update a Pull Request that modifies documentation files in one or two language directories (but not all three), the workflow will automatically:

1. **Detect** which language directories have been modified
2. **Post a comment** on the PR indicating:
   - Which languages were updated
   - Which languages are missing updates
   - Instructions for requesting and approving a translation job

### Example Workflow

**Scenario:** You update a document in `/docs/en/` but not in `/docs/zh/` or `/docs/ja/`

1. The workflow detects changes only in English docs
2. A comment is automatically posted to the PR:

```
🌍 Translation Check

This PR modifies documentation in 1 language(s):
- ✅ English (`/docs/en/`)

The following language(s) are not updated:
- ❌ Chinese (`/docs/zh/`)
- ❌ Japanese (`/docs/ja/`)

---

Should a translation job be run to update the missing language(s)?

- To request a translation job, comment: `/translate-request`
- To approve a translation job (docs-maintainers team only), comment: `/translate-approve`

> Note: Only members of the `StarRocks/docs-maintainers` team can approve translation jobs.
```

## 🔐 Permission Levels

### Anyone Can:
- **Request** a translation job by commenting `/translate-request` on the PR

### docs-maintainers Team Members Can:
- **Approve** a translation job by commenting `/translate-approve` on the PR
- This requires membership in the `StarRocks/docs-maintainers` GitHub team

## 💬 Commands

| Command | Who Can Use | Description |
|---------|-------------|-------------|
| `/translate-request` | Anyone | Request that a translation job should be run for missing languages |
| `/translate-approve` | docs-maintainers team only | Approve and trigger the translation job |

## 📋 Workflow Permissions

The workflow requires the following permissions:
- `pull-requests: write` - To comment on PRs and add labels
- `contents: read` - To read the repository contents and check file changes

## 🚀 Setting Up

### Prerequisites

1. **Create the docs-maintainers team:**
   - Go to your organization settings on GitHub
   - Navigate to Teams
   - Create a team named `docs-maintainers`
   - Add users who should be able to approve translations

2. **Workflow file location:**
   - `.github/workflows/check-translation.yml`

3. **Required directory structure:**
   ```
   docs/
   ├── en/
   ├── zh/
   └── ja/
   ```

## 🔍 How the Workflow Determines Missing Translations

The workflow compares the base branch with the PR branch and checks which files in the `/docs/en/`, `/docs/zh/`, and `/docs/ja/` directories have been modified or added.

- If changes are detected in **all 3** language directories → No comment is posted (assumes complete translation)
- If changes are detected in **1 or 2** language directories → A comment is posted asking about translation
- If changes are detected in **0** language directories (docs unchanged) → No comment is posted

## 🛠️ Customization

To customize the workflow:

1. **Change language directories**: Update the `paths` section in the workflow file
2. **Change team name**: Replace `docs-maintainers` with your team slug in the workflow
3. **Modify comment messages**: Edit the comment templates in the workflow's `script` sections

## 📝 Example Usage

### Complete Workflow Example

1. Developer creates a PR that updates `/docs/en/guide.md`
2. Workflow posts a comment noting that Chinese and Japanese versions are missing
3. Anyone comments `/translate-request` to indicate translation is needed
4. A docs-maintainers team member reviews and comments `/translate-approve`
5. The workflow confirms approval and adds the `translation-approved` label
6. (Your translation job or process would then be triggered based on this label)

## 🔗 Integration with Translation Jobs

This workflow focuses on **detection and approval**. To actually run translation jobs, you can:

1. Monitor for the `translation-approved` label
2. Trigger a separate workflow when this label is added
3. Use your preferred translation service or process
4. Create PRs with the translated content

## ⚠️ Troubleshooting

**Issue:** "Error checking team membership"
- **Solution:** Ensure the GitHub token has `read:org` scope and the team exists

**Issue:** Workflow doesn't comment on PR
- **Solution:** Verify that changes are in the docs directories and only 1-2 languages are affected

**Issue:** Approval not working
- **Solution:** Confirm user is a member of the `StarRocks/docs-maintainers` team

## 📜 License

This workflow is part of the StarRocks project.

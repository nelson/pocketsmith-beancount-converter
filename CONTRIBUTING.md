# CONTRIBUTION

# Contribution Checklist

This checklist should be followed for every code contribution submitted to GitHub.

- [ ] Summarise changes from beginning of session
- [ ] Create GitHub issue
- [ ] Create well named branch
- [ ] Run pre-commit hook
- [ ] Commit changes with message that follows this exact format:
  - **First line**: `<type>: #[ISSUE_NUMBER] [SUMMARY]`
    - `<type>` follows [Conventional Commits](https://www.conventionalcommits.org) (feat, fix, docs, etc.)
    - `[ISSUE_NUMBER]` is the GitHub issue number (e.g., #17)
    - `[SUMMARY]` is a concise one-line description
  - **Body**: Detailed description with bullet points of changes
  - **Final line**: `Closes #[ISSUE_NUMBER]`
- [ ] Create GitHub pull request based on this branch and link to the GitHub issue
- [ ] Poll for the pull request status
  - If successful, pull and checkout master, and clean up branches
  - If failed, don't pull, stay on the branch and try to fix any issues

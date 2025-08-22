This is the procedure for commiting and submitting code changes. Read each step
carefully, and follow them one by one, not skipping any steps.

  1. Run all precommit checks using `uv run pre-commit`. Fix any problems you find
  2. Study the current session context and code changes to understand what code
     is being committed, and why
  3. Create a GitHub issue with the summary from Step 1. Note down its issue
     number
  4. Create and switch to a branch that is named after the summary from Step 1
  5. Generate a commit message with the following conventional format:

    - **First line**: `<type>: #[ISSUE_NUMBER] [SUMMARY]`
      - `<type>` follows [Conventional
        Commits](https://www.conventionalcommits.org) (feat, fix, docs, etc.)
      - `[ISSUE_NUMBER]` is the GitHub issue number (e.g., #17)
      - `[SUMMARY]` is a concise one-line description
    - **Body**: Summary from step 1
    - **Final line**: `Closes #[ISSUE_NUMBER]`

  6. Create a GitHub Pull Request for this branch. Wait for the PR checks to
     complete
  7. If PR checks are successful, rebase merge the branch. Switch back to
     master and pull the latest changes. Clean up the old branch. If PR checks
     failed, fix them. Limit to 3 fix attempts with code changes. If the PR
     checks are pending, check again in 15 seconds. Limit to 4 status checks
     per code change.


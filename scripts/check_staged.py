"""Inspect staged files without printing potential credential values."""
import re
import subprocess
import sys

paths = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'], text=True).splitlines()
errors = []
for path in paths:
    if path.endswith('.pdf') or path.startswith(('.idea/', '.venv/', '.homeguide-venv/', 'data/')) or (path.startswith('.env') and path != '.env.example'):
        errors.append(f'Unintended file staged: {path}')
    content = subprocess.check_output(['git', 'show', ':' + path])
    if re.search(rb'(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY)', content):
        errors.append(f'Potential credential in {path}; inspect locally. Values withheld.')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'Inspected {len(paths)} staged files: no excluded artifacts or credential patterns found.')

# Releasing Narrative.Rx installers

The GitHub Actions workflow at `.github/workflows/build-installer.yml`
builds the Windows `.exe` and attaches it to a GitHub Release.

Two ways to trigger a release — pick whichever is easier:

---

## Option A — Tag push (recommended for real releases)

Run these commands **locally on your machine** after cloning
`https://github.com/sb-witzy/Narrative-2` (needs `git` installed):

```bash
git clone https://github.com/sb-witzy/Narrative-2.git
cd Narrative-2
git pull origin main
git tag v1.0.0
git push origin v1.0.0
```

Within ~15 minutes:
- The Actions run finishes.
- `NarrativeRx-Setup-1.0.0.exe` is attached to
  https://github.com/sb-witzy/Narrative-2/releases/tag/v1.0.0
- Release notes are auto-generated from commit messages.

For subsequent releases just bump the tag: `git tag v1.0.1`, `git push origin v1.0.1`, etc.

---

## Option B — Manual dispatch (no local git needed)

1. Open https://github.com/sb-witzy/Narrative-2/actions/workflows/build-installer.yml
2. Click **"Run workflow"** (top-right).
3. Enter the version — e.g. `1.0.0` — and click **"Run workflow"**.
4. When it finishes (~15 min), download the installer from the run's
   **Artifacts** section.

> Manual dispatch produces the `.exe` as a downloadable artifact but does
> **not** create a GitHub Release page. Use Option A for public releases.

---

## Verifying the build

- Actions status: https://github.com/sb-witzy/Narrative-2/actions
- Latest release: https://github.com/sb-witzy/Narrative-2/releases/latest
- File size will be ~250-350 MB (includes MongoDB MSI + Python venv + frontend bundle).

## If a build fails

Common causes:
- Python dependency not on PyPI mirror → check the "Create backend venv" step logs.
- Frontend `yarn build` failing → check the "Build frontend" step logs.
- Inno Setup compile error → check the "Compile installer" step logs.

The workflow currently pins:
- Python 3.12, Node 20
- MongoDB Community 7.0.14 (Windows x64)
- NSSM 2.24
- Inno Setup 6 (via Chocolatey)

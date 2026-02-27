# Build and Release (Windows)

## 1. Prerequisites
- Python 3.11+ (3.12 recommended).
- Install dependencies:
  - `pip install -r requirements-dev.txt`
- For installers:
  - NSIS (for `scripts\build_nsis.bat`),
  - Inno Setup 6 (for `scripts\build_installer.ps1`).

## 2. Mandatory quality gate before release

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

Ship a release only when this run is fully green.

## 3. Build EXE

```powershell
scripts\build_exe.bat
```

What the script does:
1. Checks that `PyInstaller` is installed.
2. Cleans `build/` and `dist/` by default.
3. Builds `EpidControl.exe`.
4. Creates `dist\RELEASE_INFO.txt` (version + timestamp).
5. Runs `scripts\verify_exe.ps1`.

Expected artifacts:
- `dist\EpidControl.exe`
- `dist\RELEASE_INFO.txt`

## 4. Build NSIS installer

```powershell
scripts\build_nsis.bat
```

Highlights:
- Version is injected from `pyproject.toml`.
- Installer has clear components:
  - required application files,
  - desktop shortcut,
  - Start Menu shortcuts.
- Uninstall metadata is written to registry.

Expected artifact:
- `dist\EpidControlSetup_NSIS.exe`

## 5. Build Inno Setup installer (optional)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

Expected artifact:
- `dist\EpidControlSetup.exe` (name comes from `OutputBaseFilename` in `installer.iss`).

## 6. Quick smoke test after build
1. Install app via NSIS or Inno installer.
2. Launch the app.
3. Verify startup, DB creation, and migrations.
4. Verify login and key tabs open correctly.
5. Run a short flow from `docs/manual_regression_scenarios.md`.

## 7. Common issues
- `makensis.exe` / `ISCC.exe` not found:
  - install NSIS/Inno Setup and add tool path to `PATH`.
- `dist\EpidControl.exe` missing when building installer:
  - run `scripts\build_exe.bat` first.
- Access denied errors:
  - run terminal as Administrator.

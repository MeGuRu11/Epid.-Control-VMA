# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_root = Path(globals().get("SPECPATH", ".")).resolve()

datas = [
    (str(project_root / "resources"), "resources"),
    (str(project_root / "app" / "image"), "app/image"),
    (
        str(project_root / "app" / "infrastructure" / "db" / "migrations"),
        "app/infrastructure/db/migrations",
    ),
    (str(project_root / "alembic.ini"), "."),
]

hiddenimports = [
    "sqlite3",
    "sqlalchemy.dialects.sqlite",
]
hiddenimports += collect_submodules("alembic")


a = Analysis(
    ["app/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="EpidControl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_root / "resources" / "icons" / "app.ico"),
)

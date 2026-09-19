import os
import shutil
import sys
import platform
import tempfile
from importlib.util import find_spec

import cx_Freeze
from cx_Freeze import Executable, setup

try:
    from cx_Freeze.command.bdist_dmg import bdist_dmg as BdistDMG
except ImportError:  # pragma: no cover - available only on macOS
    BdistDMG = None

from sportorg import config


def resolve_macos_icon() -> str:
    """Return the best available macOS app icon or the current fallback."""
    candidates = [
        os.path.join(config.ICON_DIR, "sportorg.icns"),
        os.path.join(config.ICON_DIR, "SportOrg.icns"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    for root, _, files in os.walk(config.ICON_DIR):
        for name in sorted(files):
            if name.lower().endswith(".icns"):
                return os.path.join(root, name)

    return config.icon_dir("sportorg.ico")


CXFREEZE_MAJOR = int(cx_Freeze.__version__.split(".")[0])

base = None
if sys.platform == "win32":
    # The GUI base was renamed in cx_Freeze 8.0 and no fallback ships: 6.x/7.x
    # only have "Win32GUI", 8.x only has "gui".
    base = "gui" if CXFREEZE_MAJOR >= 8 else "Win32GUI"
elif sys.platform == "darwin":
    # No base needed for macOS (macOS apps don't open console by default in App bundle)
    base = None

include_files = [
    (config.base_dir("sportorg", "data"), "lib/sportorg/data"),
    config.base_dir("LICENSE"),
    config.base_dir("changelog.md"),
    config.base_dir("changelog_ru.md"),
    config.COMMIT_VERSION_FILE,
]
includes = ["atexit", "codecs", "playsound3"]

if sys.platform == "win32":
    includes.append("pyImpinj")

if find_spec("sportorg_rust_example") is not None:
    includes.append("sportorg_rust_example")
if find_spec("sportorg_core") is not None:
    includes.append("sportorg_core")
excludes = ["Tkinter", "unittest", "test", "pydoc"]
qt_binding = "PySide6" if find_spec("PySide6") is not None else "PySide2"
excludes.append("PySide2" if qt_binding == "PySide6" else "PySide6")

build_exe_options = {
    "includes": includes,
    "excludes": excludes,
    "packages": ["idna", "requests", "encodings", "asyncio"],
    "include_files": include_files,
    "zip_include_packages": [qt_binding],
    "optimize": 2,
    "silent": 1,
}

if sys.platform == "win32":
    build_exe_options["include_msvcr"] = True
    build_exe_options["packages"].append("pywinusb")

GENERIC_ALL = 0x10000000
WRITABLE_DIRS = [
    ("DataDir", "data"),
    ("LogDir", "logs"),
]

UPGRADE_CODE = "{D652DEE1-13E6-4D7A-B8FC-334FF475E5FD}"

bdist_msi_options = {
    "all_users": True,
    "upgrade_code": UPGRADE_CODE,
    "initial_target_dir": r"[ProgramFiles64Folder]\{}".format(config.NAME),
    "data": {
        "Directory": [(logical, "TARGETDIR", name) for logical, name in WRITABLE_DIRS],
        "CreateFolder": [(logical, "TARGETDIR") for logical, _ in WRITABLE_DIRS],
        "LockPermissions": [
            (logical, "CreateFolder", None, "Everyone", GENERIC_ALL)
            for logical, _ in WRITABLE_DIRS
        ],
        "Shortcut": [
            (
                "DesktopShortcut",  # Shortcut
                "DesktopFolder",  # Directory
                config.NAME,  # Name
                "TARGETDIR",  # Component
                "[TARGETDIR]SportOrg.exe",  # Target
                None,  # Arguments
                None,  # Description
                None,  # Hotkey
                None,  # Icon
                None,  # IconIndex
                None,  # ShowCmd
                "TARGETDIR",  # WkDir
            ),
        ],
    },
}

bdist_mac_options = {
    "bundle_name": config.NAME,
    "iconfile": resolve_macos_icon(),
}

bdist_dmg_options = {
    "volume_label": config.NAME,
    "applications_shortcut": True,
    "format": "UDZO",
    "filesystem": "HFS+",
}


if CXFREEZE_MAJOR >= 8:
    msi_platform = platform.machine().lower() or "windows"
    bdist_msi_options["output_name"] = "{}-{}-{}.msi".format(
        config.NAME.lower(), config.VERSION.lstrip("v"), msi_platform
    )


options = {
    "build_exe": build_exe_options,
    "bdist_msi": bdist_msi_options,
    "bdist_mac": bdist_mac_options,
    "bdist_dmg": bdist_dmg_options,
}

executables = [
    Executable(
        "SportOrg.py",
        base=base,
        icon=resolve_macos_icon() if sys.platform == "darwin" else config.icon_dir("sportorg.ico"),
        copyright="GNU GENERAL PUBLIC LICENSE {}".format(config.NAME),
    )
]

if sys.platform == "win32":
    from cx_Freeze.command.bdist_msi import BdistMSI

    class BdistMSINonAscii(BdistMSI):
        def add_files(self):
            import msilib

            original = msilib.FCICreate

            def fcicreate(cabname, files):
                stage = None
                staged = []
                try:
                    for source, logical in files:
                        try:
                            source.encode("ascii")
                        except UnicodeEncodeError:
                            if stage is None:
                                stage = tempfile.mkdtemp(prefix="cxfreeze-cab-")
                            ascii_source = os.path.join(
                                stage, "%05d.bin" % len(staged)
                            )
                            shutil.copyfile(source, ascii_source)
                            source = ascii_source
                        staged.append((source, logical))
                    return original(cabname, staged)
                finally:
                    if stage is not None:
                        shutil.rmtree(stage, ignore_errors=True)

            msilib.FCICreate = fcicreate
            try:
                super().add_files()
            finally:
                msilib.FCICreate = original

    cmdclass = {"bdist_msi": BdistMSINonAscii}
else:
    cmdclass = {}

if BdistDMG is not None:
    cmdclass["bdist_dmg"] = BdistDMG


def main() -> int:
    if len(sys.argv) == 1:
        print(
            "No build command supplied. Use: python builder.py build, "
            "python builder.py bdist_msi, or python builder.py bdist_dmg",
            file=sys.stderr,
        )
        return 1

    command = sys.argv[1]
    supported_commands = {"build", "build_exe", "bdist_msi", "bdist_mac", "bdist_dmg"}

    if command not in supported_commands:
        print(
            f"Unsupported command: {command}. Supported commands: "
            f"{', '.join(sorted(supported_commands))}",
            file=sys.stderr,
        )
        return 2

    if command == "bdist_dmg" and BdistDMG is None:
        print(
            "The bdist_dmg command is available only on macOS. Use build or bdist_msi on this platform.",
            file=sys.stderr,
        )
        return 3

    setup(
        name=config.NAME,
        version=config.VERSION,
        description=config.NAME,
        options=options,
        executables=executables,
        cmdclass=cmdclass,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

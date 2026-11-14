"""Build-artifact verification used by the cross-platform CI matrix."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path


def main() -> int:
    dist = Path("dist")
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(dist)],
        check=True,
    )
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit(
            f"Expected exactly one wheel and one .tar.gz sdist; "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)."
        )

    artifacts = [*wheels, *sdists]
    subprocess.run(
        [sys.executable, "-m", "twine", "check", *(str(path) for path in artifacts)],
        check=True,
    )

    with zipfile.ZipFile(wheels[0]) as archive:
        if "chronos/__init__.py" not in archive.namelist():
            raise SystemExit("Built wheel is missing chronos/__init__.py.")

    with tarfile.open(sdists[0], "r:gz") as archive:
        if not any(name.endswith("/src/chronos/__init__.py") for name in archive.getnames()):
            raise SystemExit("Built source distribution is missing src/chronos/__init__.py.")

    with tempfile.TemporaryDirectory(prefix="chronos-wheel-smoke-") as temp_dir:
        environment = Path(temp_dir) / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheels[0].resolve())],
            check=True,
        )
        smoke = (
            "from importlib.metadata import version; "
            "import chronos; "
            "assert version('chronos-temporal-computing-engine') == chronos.__version__; "
            "print('Installed wheel import OK:', chronos.__version__)"
        )
        subprocess.run([str(python), "-c", smoke], cwd=temp_dir, check=True)

    print(f"Verified wheel: {wheels[0]}")
    print(f"Verified source distribution: {sdists[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

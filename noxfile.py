import tempfile
from pathlib import Path

import nox


nox.options.default_venv_backend = "none"


@nox.session
def install(session):
    session.run_always("poetry", "install")


@nox.session
def black(session):
    session.run("poetry", "run", "black", "--check", ".")


@nox.session
def isort(session):
    session.run("poetry", "run", "isort", "--check", ".")


@nox.session
def flake8(session):
    session.run("poetry", "run", "flake8")


@nox.session
def mypy(session):
    session.run("poetry", "run", "mypy", ".")


@nox.session
def pytest(session):
    session.run("poetry", "run", "pytest")


@nox.session
def safety(session):
    with tempfile.TemporaryDirectory(prefix="nox_") as tmpdir:
        requirements = Path(tmpdir) / "requirements.txt"
        session.run(
            "poetry",
            "export",
            "--dev",
            "--format=requirements.txt",
            f"--output={requirements}",
        )
        session.run(
            "safety",
            "check",
            f"--file={requirements}",
            "--full-report",
            env={"COLUMNS": "79"},
        )

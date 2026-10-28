import io

from rich.console import Console

from aspare.terminal import THEME, main


def _run(*args: str) -> tuple[int, str]:
    buf = io.StringIO()
    console = Console(file=buf, width=120, theme=THEME, force_terminal=False)
    code = main(["--mode", "demo", "--speed", "0", *args], console=console)
    return code, buf.getvalue()


def test_demo_is_a_dry_run_by_default():
    code, out = _run()
    assert code == 0
    assert "Dry run" in out
    assert "VERIFIED" not in out


def test_demo_fix_verifies_and_holds_intended_public_bucket():
    code, out = _run("--fix", "--yes")
    assert code == 0
    assert out.count("VERIFIED") >= 4
    assert "held" in out and "campus-marketing-site" in out

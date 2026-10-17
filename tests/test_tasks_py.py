"""Task metadata ends at the first blank line after its heading."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "tasks_cli", Path(__file__).resolve().parents[1] / "scripts" / "tasks.py"
)
tasks_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tasks_cli)


@pytest.mark.parametrize("blank", ["", "   "])
def test_body_bullets_are_not_fields(blank):
    text = (
        "### T001 — Example\n- status: claimed\n- owner: worker\n"
        f"{blank}\nAcceptance:\n- foo: bar\n- status: x\n"
        "\n### T002 — Next\n- status: todo\n\nBody\n## Other\n"
    )
    lines, tasks = tasks_cli.parse(text)
    assert tasks["T001"]["vals"] == {"status": "claimed", "owner": "worker"}
    assert tasks["T002"]["vals"] == {"status": "todo"}
    updated = tasks_cli.set_fields(lines, tasks["T001"], {"note": "reviewed"})
    assert "\n".join(updated) == text.replace(
        "- owner: worker\n", "- owner: worker\n- note: reviewed\n"
    )
    assert tasks_cli.block(lines, tasks["T001"]) == text.split("\n### T002")[0].rstrip()


def test_show_preserves_header_status_and_body(monkeypatch, capsys):
    text = "### T001 — Example\n- status: claimed\n\n- foo: bar\n- status: x\n"
    monkeypatch.setattr(tasks_cli, "sync", lambda: None)
    monkeypatch.setattr(tasks_cli, "load", lambda: tasks_cli.parse(text))
    monkeypatch.setattr("sys.argv", ["tasks.py", "show", "T001"])
    tasks_cli.main()
    assert capsys.readouterr().out == text

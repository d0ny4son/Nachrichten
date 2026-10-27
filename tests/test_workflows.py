from pathlib import Path

import yaml

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def load(name):
    data = yaml.safe_load((WF / name).read_text(encoding="utf-8"))
    # PyYAML liest den Schlüssel „on“ als True
    data["on"] = data.pop(True, data.get("on"))
    return data


def steps(wf):
    return [s for job in wf["jobs"].values() for s in job.get("steps", [])]


def test_collect_schedule_and_deploy():
    wf = load("collect.yml")
    assert wf["on"]["schedule"][0]["cron"] == "*/20 * * * *"
    assert "workflow_dispatch" in wf["on"]
    uses = [s.get("uses", "") for s in steps(wf)]
    assert any("deploy-pages" in u for u in uses)
    assert any("upload-pages-artifact" in u for u in uses)


def test_collect_excludes_state_from_pages():
    wf = load("collect.yml")
    copy = [s for s in steps(wf) if "_site" in str(s.get("run", ""))]
    assert copy, "Kopierschritt nach _site fehlt"
    assert "state.json" in copy[0]["run"]


def test_keepalive_reenables_collect():
    text = (WF / "keepalive.yml").read_text(encoding="utf-8")
    assert "/enable" in text
    assert "actions: write" in text


def test_validate_runs_both_test_suites():
    text = (WF / "validate.yml").read_text(encoding="utf-8")
    assert "pytest" in text
    assert "npm test" in text

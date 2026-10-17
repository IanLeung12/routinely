import pytest

from routine_watch import alerts as alerts_module
from routine_watch.alerts import build_alerts
from routine_watch.demo import demo_residents
from routine_watch.explain import TemplateExplainer

#: Both tests need a flagged demo resident to summarise (T124: the seeded demo
#: alone leaves mrs-k on watch, not flagged).
pytestmark = pytest.mark.usefixtures("mrs_k_flagged")


def test_build_alerts_defaults_to_template_output(monkeypatch):
    """With LIVE_API unset, get_explainer() resolves to TemplateExplainer, so the
    default summaries equal what an explicit TemplateExplainer produces."""
    residents = demo_residents()
    default_summaries = [alert.summary for alert in build_alerts(residents)]

    monkeypatch.setattr(alerts_module, "_get_explainer", lambda: TemplateExplainer())
    template_summaries = [alert.summary for alert in build_alerts(residents)]

    assert default_summaries == template_summaries
    assert default_summaries


def test_build_alerts_uses_monkeypatched_explainer(monkeypatch):
    """Swapping the module-level helper swaps the explainer every alert uses."""

    class FakeExplainer:
        def summarise(self, errors, baseline, context):
            return "FAKE"

    monkeypatch.setattr(alerts_module, "_get_explainer", lambda: FakeExplainer())

    alerts = build_alerts(demo_residents())

    assert alerts
    assert all(alert.summary == "FAKE" for alert in alerts)

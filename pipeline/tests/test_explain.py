from routine_watch.explain import TemplateExplainer


def test_mentions_every_error_with_timestamp():
    errors = [
        {"type": "omission", "step_id": "teabag_in_cup", "t_start": 42},
        {"type": "perseveration", "step_id": "pour", "t_start": 75},
    ]
    baseline = {"observed": 2, "baseline_mean": 0.2, "baseline_days": 14}
    result = TemplateExplainer().summarise(errors, baseline, [])

    assert "skipped teabag in cup at 0:42" in result
    assert "repeated pour at 1:15" in result
    assert "0.2" in result
    assert "14" in result


def test_unknown_error_type_falls_back_to_type_and_step():
    errors = [{"type": "mystery", "step_id": "pour_water", "t_start": 5}]
    baseline = {"observed": 1, "baseline_mean": 0.2, "baseline_days": 14}
    result = TemplateExplainer().summarise(errors, baseline, [])

    assert "mystery at pour water at 0:05" in result


def test_includes_context_only_when_given():
    errors = [{"type": "omission", "step_id": "teabag_in_cup", "t_start": 42}]
    baseline = {"observed": 1, "baseline_mean": 0.2, "baseline_days": 14}

    with_context = TemplateExplainer().summarise(
        errors, baseline, ["new antibiotic started 2 days ago"]
    )
    assert "new antibiotic started 2 days ago" in with_context

    without_context = TemplateExplainer().summarise(errors, baseline, [])
    assert "Context" not in without_context


def test_never_mentions_diagnosis_or_unstated_facts():
    errors = [{"type": "omission", "step_id": "teabag_in_cup", "t_start": 42}]
    baseline = {"observed": 1, "baseline_mean": 0.2, "baseline_days": 14}
    result = TemplateExplainer().summarise(errors, baseline, [])

    assert "diagnos" not in result.lower()


def test_empty_errors_gives_no_errors_sentence():
    baseline = {"observed": 0, "baseline_mean": 0.2, "baseline_days": 14}
    result = TemplateExplainer().summarise([], baseline, [])

    assert "no errors" in result.lower()
    assert "0.2" in result
    assert "14" in result

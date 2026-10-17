"""The routine builder (SPEC sections 7 and 12): a routine from words or one setup clip.

Three things are being held here. That a draft - a model's own words, trusted with
nothing - always comes out as a graph `tasks/graph.py` would load: ids slugged,
dependencies only ever backwards, objects mapped onto classes the detector was
actually trained on and the rest listed as `needs_training`. That a mangled answer is
refused with a reason somebody can act on rather than half-built. And that a setup
clip is a one-time, opt-in step that never lands anywhere: no consent, no read; with
consent, nothing new under the repo, the data directories or the temp directory
afterwards.

Nothing here reaches the network. The offline `FixtureDrafter` does most of the work,
stub drafters supply the answers a real model would get wrong, and `GeminiDrafter`
and `ClaudeDrafter` are exercised over an `httpx2.MockTransport` and a fake client.
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from routine_watch import routine_builder
from routine_watch.api import app
from routine_watch.api_routines import CONSENT_REQUIRED
from routine_watch.contracts import ObjectLabel, repo_root
from routine_watch.routine_builder import (
    FIXTURES_DIR,
    MAX_STEPS,
    MAX_VIDEO_BYTES,
    ClaudeDrafter,
    ClipRejected,
    DrafterAnswer,
    DraftStep,
    FixtureDrafter,
    GeminiDrafter,
    LiveDrafter,
    Routine,
    RoutineBuilderError,
    RoutineDraft,
    RoutineStore,
    build_routine,
    built_in_routines,
    detector_class,
    draft_from_text,
    draft_from_video,
    get_drafter,
    slug,
    to_task_graph,
    use_drafter,
    use_routine_store,
)
from routine_watch.tasks.graph import TaskGraphError, parse_task_data

#: A marker the privacy test can look for, built in two halves so this file is not
#: itself a file that "holds the clip" (`explain_claude.py` splits a literal the same
#: way, for the same reason).
CLIP_MARKER = b"ROUTINE-WATCH-" + b"SETUP-CLIP-MARKER"

#: Big enough that Starlette spools the upload to a real temp file: it keeps an upload
#: in memory up to a megabyte, and that temp file is the thing that has to be deleted.
BIG_CLIP = CLIP_MARKER + b"\x00\x01\x02\x03" * 400_000

SMALL_CLIP = CLIP_MARKER + b"\x00" * 2048


@pytest.fixture(autouse=True)
def _own_routines_dir(tmp_path, monkeypatch):
    """Nothing in this file may write a routine into the repo: every test gets its
    own `ROUTINES_DIR` and a store built fresh from it."""
    monkeypatch.setenv("ROUTINES_DIR", str(tmp_path / "routines"))
    monkeypatch.setenv("API_CACHE_DIR", str(tmp_path / "cache"))
    use_routine_store(None)
    use_drafter(None)
    yield
    use_routine_store(None)
    use_drafter(None)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


class StubDrafter:
    """A drafter that answers with whatever a test hands it, and counts the asking."""

    def __init__(self, payload: object = None, provider: str = "stub") -> None:
        self.payload = payload
        self.provider = provider
        self.text_calls: list[str] = []
        self.video_calls: list[tuple[int, str, str | None]] = []

    def draft_text(self, description: str) -> DrafterAnswer:
        self.text_calls.append(description)
        return DrafterAnswer(payload=self.payload, provider=self.provider)

    def draft_video(
        self, video: bytes, mime: str, description: str | None = None
    ) -> DrafterAnswer:
        self.video_calls.append((len(video), mime, description))
        return DrafterAnswer(payload=self.payload, provider=self.provider)


def _answer(*steps: dict, title: str = "A routine") -> dict:
    return {"title": title, "steps": list(steps)}


def _step(label: str, **overrides) -> dict:
    """One step of an answer. `objects` defaults to something the detector knows, so a
    test about dependencies is not also a test about the hands fallback."""
    return {"label": label, "objects": ["cup"], "depends_on": [], **overrides}


# ------------------------------------------------------- words in, task graph out


def test_a_described_routine_becomes_a_graph_the_loader_accepts():
    draft = draft_from_text("I brush my teeth every morning")

    assert draft.source == "text"
    assert draft.provider == "fixture:brush_teeth"
    assert draft.title == "Brush your teeth"

    graph = to_task_graph(draft)
    parsed = parse_task_data(graph)  # the same loader that reads tasks/tea.yaml
    assert parsed.id == "brush_your_teeth"
    assert parsed.title == "Brush your teeth"
    assert parsed.step_ids[0] == "get_the_toothbrush"
    assert parsed.is_optional("rinse_the_brush")
    assert not parsed.is_once_only("brush_your_teeth")
    # A correct run of it exists, which is what the error classifier needs.
    assert parsed.is_valid_order(list(parsed.required_steps))


def test_a_draft_only_ever_depends_on_steps_the_routine_already_has():
    draft = draft_from_text("show me making a cup of tea")
    graph = to_task_graph(draft)

    seen: set[str] = set()
    for step in graph["steps"]:
        assert set(step["deps"]) <= seen, step
        seen.add(step["id"])


def test_objects_the_detector_knows_are_mapped_and_the_rest_need_training():
    tea = build_routine(draft_from_text("I make a cup of tea with a tea bag"))

    # "mug", "tea bag" and "teaspoon" are everyday names for classes it has.
    assert tea.needs_training == ()
    objects = {step["id"]: step["objects"] for step in tea.graph["steps"]}
    assert objects["get_a_mug"] == ["cup"]
    assert objects["put_the_tea_bag_in_the_mug"] == ["teabag", "cup"]
    assert objects["stir_it"] == ["spoon", "cup"]
    known = {str(label) for label in ObjectLabel}
    assert all(set(names) <= known for names in objects.values())

    toast = build_routine(draft_from_text("I put bread in the toaster"))
    assert toast.needs_training == ("bread", "toaster", "plate", "butter", "knife")


def test_a_step_with_nothing_the_detector_knows_watches_the_hands():
    built = build_routine(draft_from_text("toast for breakfast"))

    objects = {step["id"]: step["objects"] for step in built.graph["steps"]}
    assert objects["get_the_bread_out"] == [str(ObjectLabel.HAND)]
    assert any("watches the hands" in warning for warning in built.warnings)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("kettle", "kettle"),
        ("Mug", "cup"),
        ("tea bag", "teabag"),
        ("tea_bag", "teabag"),
        ("teaspoons", "spoon"),
        ("dosette box", "pill_organiser"),
        ("hands", "hand"),
        ("cups", "cup"),
        ("toothbrush", None),
        ("", None),
    ],
)
def test_everyday_object_names_map_onto_detector_classes(name, expected):
    assert detector_class(name) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Get a mug!", "get_a_mug"),
        ("  Fill the kettle  ", "fill_the_kettle"),
        ("Café au lait", "cafe_au_lait"),
        ("2 slices of bread", "step_2_slices_of_bread"),
        ("***", ""),
        ("", ""),
    ],
)
def test_step_ids_are_slugged_into_what_the_loader_accepts(text, expected):
    assert slug(text) == expected


# ----------------------------------------------- what the builder has to hold a draft to


def test_a_dependency_on_a_later_or_unknown_step_is_dropped_and_said_out_loud():
    drafter = StubDrafter(
        _answer(
            _step("Get a cup", depends_on=["Pour the water"]),  # not placed yet
            _step("Pour the water", depends_on=["Get a cup", "Boil the kettle"]),  # one invented
            _step("Stir", depends_on=["Stir"]),  # itself
        )
    )
    built = build_routine(draft_from_text("anything", drafter))

    deps = {step["id"]: step["deps"] for step in built.graph["steps"]}
    assert deps == {"get_a_cup": [], "pour_the_water": ["get_a_cup"], "stir": []}
    assert len(built.warnings) == 3
    assert all("no earlier step" in warning for warning in built.warnings)
    parse_task_data(built.graph)


def test_a_required_step_is_never_left_waiting_on_an_optional_one():
    drafter = StubDrafter(
        _answer(
            _step("Add sugar", optional=True),
            _step("Stir it in", depends_on=["Add sugar"]),
        )
    )
    built = build_routine(draft_from_text("anything", drafter))

    assert [step["deps"] for step in built.graph["steps"]] == [[], []]
    assert any("cannot wait on an optional one" in warning for warning in built.warnings)
    # The loader refuses that shape outright, so the graph would not load otherwise.
    parse_task_data(built.graph)


def test_two_steps_with_the_same_label_get_distinct_ids():
    drafter = StubDrafter(_answer(_step("Rinse"), _step("Rinse"), _step("Rinse")))
    built = build_routine(draft_from_text("anything", drafter))

    assert [step["id"] for step in built.graph["steps"]] == ["rinse", "rinse_2", "rinse_3"]
    assert len(built.warnings) == 2
    parse_task_data(built.graph)


def test_a_step_whose_label_slugs_to_nothing_still_gets_an_id():
    drafter = StubDrafter(_answer(_step("***"), _step("###")))
    built = build_routine(draft_from_text("anything", drafter))

    assert [step["id"] for step in built.graph["steps"]] == ["step", "step_2"]
    parse_task_data(built.graph)


def test_a_duplicate_dependency_is_listed_once():
    drafter = StubDrafter(
        _answer(_step("Get a cup"), _step("Pour", depends_on=["Get a cup", "get_a_cup"]))
    )
    built = build_routine(draft_from_text("anything", drafter))

    assert built.graph["steps"][1]["deps"] == ["get_a_cup"]


def test_a_routine_with_no_title_is_named_after_the_words_it_came_from():
    drafter = StubDrafter({"steps": [_step("Feed the cat", objects=["bowl"])]})
    draft = draft_from_text("i feed the cat at six, then i fill the water bowl", drafter)

    assert draft.title == "I feed the cat at six, then i fill the water bowl"
    assert to_task_graph(draft)["id"] == "i_feed_the_cat_at_six_then_i_fill_the"


def test_a_routine_with_no_name_at_all_still_loads():
    """A draft a caller built by hand can have no title; the graph still has to be one
    the loader accepts, so the builder names the routine rather than refusing it."""
    draft = RoutineDraft(
        title="",
        steps=(DraftStep(label="Do it", objects=("cup",)),),
        source="text",
        provider="test",
    )
    graph = to_task_graph(draft)

    assert graph["id"] == "new_routine"
    assert parse_task_data(graph).title == "New routine"


# -------------------------------------------------- a mangled answer, refused clearly


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("not json at all", "was not JSON"),
        ('{"steps": []}', "steps"),
        ({"steps": []}, "steps"),
        ({"steps": [{"objects": ["cup"]}]}, "label"),
        ({"steps": [{"label": ""}]}, "label"),
        ({"steps": "fill the kettle"}, "steps: Input should be a valid list"),
        ([{"label": "Get a cup"}], "not a JSON object with a list of steps"),
        (None, "not a JSON object with a list of steps"),
        (42, "not a JSON object with a list of steps"),
        ({"steps": [{"label": "Step"}] * (MAX_STEPS + 1)}, "steps"),
    ],
)
def test_an_answer_that_is_not_a_routine_is_refused_with_a_reason(payload, expected):
    with pytest.raises(RoutineBuilderError) as refusal:
        draft_from_text("anything", StubDrafter(payload))

    assert "the draft was not" in str(refusal.value)
    assert expected in str(refusal.value)


def test_json_the_model_wrapped_in_a_fence_or_a_sentence_is_still_read():
    fenced = "```json\n" + json.dumps(_answer(_step("Get a cup", objects=["mug"]))) + "\n```"
    chatty = "Sure! Here you go: " + json.dumps(_answer(_step("Get a cup"))) + " Hope that helps."

    for payload in (fenced, chatty):
        draft = draft_from_text("anything", StubDrafter(payload))
        assert [step.label for step in draft.steps] == ["Get a cup"]


def test_one_object_where_a_list_was_asked_for_is_read_as_a_list_of_one():
    drafter = StubDrafter(
        {
            "title": "Tea",
            "steps": [
                {"label": "Get a mug", "objects": "mug"},
                {"label": "Pour", "deps": "Get a mug", "objects": ["kettle"]},
            ],
        }
    )
    built = build_routine(draft_from_text("anything", drafter))

    assert built.graph["steps"][0]["objects"] == ["cup"]
    assert built.graph["steps"][1]["deps"] == ["get_a_mug"]


def test_keys_a_model_volunteers_are_ignored_rather_than_refused():
    drafter = StubDrafter(
        {
            "title": "Tea",
            "confidence": 0.8,
            "steps": [{"label": "Get a mug", "objects": ["mug"], "duration_s": 4}],
        }
    )
    assert draft_from_text("anything", drafter).title == "Tea"


@pytest.mark.parametrize("description", ["", "   ", None])
def test_an_empty_description_is_refused_before_any_model_is_asked(description):
    drafter = StubDrafter(_answer(_step("Get a cup")))
    with pytest.raises(RoutineBuilderError, match="describe the routine"):
        draft_from_text(description, drafter)
    assert drafter.text_calls == []


def test_a_description_longer_than_the_cap_is_refused():
    drafter = StubDrafter(_answer(_step("Get a cup")))
    with pytest.raises(RoutineBuilderError, match="under 2000 characters"):
        draft_from_text("tea " * 1000, drafter)
    assert drafter.text_calls == []


# ------------------------------------------------------------- one setup clip, capped


def test_a_clip_is_drafted_from_and_the_bytes_are_only_passed_through():
    drafter = StubDrafter(_answer(_step("Get the brush", objects=["toothbrush"])))
    draft = draft_from_video(SMALL_CLIP, "video/mp4", description="brushing", drafter=drafter)

    assert draft.source == "video"
    assert drafter.video_calls == [(len(SMALL_CLIP), "video/mp4", "brushing")]
    assert build_routine(draft).needs_training == ("toothbrush",)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"mime": "video/mp4", "duration_s": 61.0}, "at most 60 seconds"),
        ({"mime": "image/png"}, "not a video"),
    ],
)
def test_a_clip_outside_one_setup_step_is_refused_unread(kwargs, expected):
    drafter = StubDrafter(_answer(_step("Get the brush")))
    with pytest.raises(ClipRejected, match=expected):
        draft_from_video(SMALL_CLIP, drafter=drafter, **kwargs)
    assert drafter.video_calls == []


def test_a_clip_over_the_byte_cap_is_refused_unread():
    drafter = StubDrafter(_answer(_step("Get the brush")))
    with pytest.raises(ClipRejected, match="at most 20 MB"):
        draft_from_video(b"\x00" * (MAX_VIDEO_BYTES + 1), drafter=drafter)
    assert drafter.video_calls == []


def test_an_empty_clip_is_refused():
    with pytest.raises(RoutineBuilderError, match="empty"):
        draft_from_video(b"", drafter=StubDrafter(_answer(_step("x"))))


# ------------------------------------------------------------ the offline fake default


def test_the_default_drafter_is_the_offline_fake(monkeypatch):
    monkeypatch.setenv("LIVE_API", "0")
    monkeypatch.setenv("GEMINI_API_KEY", "not-used")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-used")
    assert isinstance(get_drafter(), FixtureDrafter)


def test_only_live_api_reaches_a_real_model(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    assert isinstance(get_drafter(), LiveDrafter)


def test_use_drafter_is_what_everything_else_goes_through():
    stub = StubDrafter(_answer(_step("Get a cup")))
    use_drafter(stub)
    assert get_drafter() is stub
    assert draft_from_text("anything").provider == "stub"


def test_a_description_that_matches_nothing_falls_back_and_says_so():
    draft = draft_from_text("I water the plants on the balcony")

    assert draft.provider == "fixture:make_toast"
    assert len(draft.notes) == 1
    assert "nothing in this description matched one" in draft.notes[0]
    assert "LIVE_API=1" in draft.notes[0]


def test_a_clip_with_no_caption_stands_in_for_the_built_in_example():
    draft = draft_from_video(SMALL_CLIP, "video/mp4")

    assert draft.provider == f"fixture:{routine_builder.DEFAULT_CLIP_FIXTURE}"
    assert "the clip was not sent anywhere" in draft.notes[0]


def test_a_clip_with_a_caption_is_drafted_from_the_caption_offline():
    draft = draft_from_video(SMALL_CLIP, "video/mp4", description="this is me making tea")

    assert draft.provider == "fixture:make_tea"
    assert draft.notes == ()


def test_every_canned_draft_builds_a_graph_the_loader_accepts():
    canned = sorted(FIXTURES_DIR.glob("*.json"))
    assert len(canned) >= 2, "the offline demo needs more than one canned routine"

    for path in canned:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["keywords"], f"{path.name} can never be picked"
        draft = draft_from_text("anything", StubDrafter(data["answer"]))
        parse_task_data(to_task_graph(draft), source=path.name)

    assert sum(json.loads(p.read_text())["default"] for p in canned) == 1


def test_a_fixture_directory_with_nothing_in_it_is_a_clear_error(tmp_path):
    with pytest.raises(RoutineBuilderError, match="no canned routine drafts"):
        draft_from_text("tea", FixtureDrafter(directory=tmp_path))


def test_a_fixture_file_that_is_not_a_draft_is_a_clear_error(tmp_path):
    (tmp_path / "broken.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RoutineBuilderError, match="not a canned routine draft"):
        draft_from_text("tea", FixtureDrafter(directory=tmp_path))


# ------------------------------------------------ the real providers, over stubbed I/O


def _gemini_reply(answer: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]}


def test_gemini_reads_a_clip_inline_and_caches_only_its_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    sent: list[dict] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        assert request.headers["x-goog-api-key"] == "key-123"
        answer = _answer(_step("Get a mug", objects=["mug"]))
        return httpx2.Response(200, json=_gemini_reply(answer))

    cache = tmp_path / "cache"
    drafter = GeminiDrafter(
        api_key="key-123",
        model="gemini-2.5-flash-lite",
        transport=httpx2.MockTransport(handle),
        cache_dir=cache,
    )
    draft = draft_from_video(SMALL_CLIP, "video/mp4", description="brushing", drafter=drafter)

    assert draft.provider == "gemini:gemini-2.5-flash-lite"
    assert draft.steps[0].label == "Get a mug"

    parts = sent[0]["contents"][0]["parts"]
    assert parts[0]["inline_data"]["mime_type"] == "video/mp4"
    assert base64.b64decode(parts[0]["inline_data"]["data"]) == SMALL_CLIP
    assert "brushing" in parts[1]["text"]
    assert "JSON" in parts[1]["text"]

    # Only Gemini's answer is kept, and the clip is not in it or in the key.
    cached = [path for path in cache.rglob("*.json")]
    assert len(cached) == 1
    blob = cached[0].read_bytes()
    assert CLIP_MARKER not in blob
    assert base64.b64encode(SMALL_CLIP) not in blob
    assert b"Get a mug" in blob

    # A second identical draft is answered out of the cache, not out of the network.
    sent.clear()
    draft_from_video(SMALL_CLIP, "video/mp4", description="brushing", drafter=drafter)
    assert sent == []


def test_gemini_drafts_from_words_too(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    transport = httpx2.MockTransport(
        lambda request: httpx2.Response(200, json=_gemini_reply(_answer(_step("Boil it"))))
    )
    drafter = GeminiDrafter(api_key="k", transport=transport, cache_dir=tmp_path)

    assert draft_from_text("make tea", drafter).steps[0].label == "Boil it"


def test_an_answer_gemini_never_gave_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    transport = httpx2.MockTransport(lambda request: httpx2.Response(200, json={}))
    drafter = GeminiDrafter(api_key="k", transport=transport, cache_dir=tmp_path)

    with pytest.raises(RoutineBuilderError, match="did not answer with a routine"):
        draft_from_text("make tea", drafter)


def test_a_gemini_failure_is_never_cached_as_an_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    transport = httpx2.MockTransport(lambda request: httpx2.Response(503, text="busy"))
    drafter = GeminiDrafter(api_key="k", transport=transport, cache_dir=tmp_path)

    with pytest.raises(httpx2.HTTPStatusError):
        draft_from_text("make tea", drafter)
    assert list(tmp_path.rglob("*.json")) == []


def test_claude_drafts_from_words_over_a_fake_client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    asked: list[dict] = []

    class FakeMessages:
        def create(self, **kwargs):
            asked.append(kwargs)
            text = json.dumps(_answer(_step("Get a mug", objects=["mug"]), title="Tea"))
            return type("Reply", (), {"content": [type("Block", (), {"text": text})()]})()

    client = type("FakeAnthropic", (), {"messages": FakeMessages()})()
    drafter = ClaudeDrafter(client=client, model="claude-haiku-4-5", cache_dir=tmp_path)
    draft = draft_from_text("I make a cup of tea", drafter)

    assert draft.provider == "anthropic:claude-haiku-4-5"
    assert draft.title == "Tea"
    assert asked[0]["model"] == "claude-haiku-4-5"
    assert "I make a cup of tea" in asked[0]["messages"][0]["content"]


def test_claude_sends_a_setup_clip_to_gemini_instead_of_reading_it():
    with pytest.raises(RoutineBuilderError, match="GEMINI_API_KEY"):
        ClaudeDrafter(client=object()).draft_video(SMALL_CLIP, "video/mp4")


def test_a_clip_with_no_gemini_key_is_refused_rather_than_held(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RoutineBuilderError, match="GEMINI_API_KEY"):
        LiveDrafter().draft_video(SMALL_CLIP, "video/mp4")


def test_words_with_no_key_at_all_fall_back_to_the_offline_fake(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert LiveDrafter().draft_text("make tea").provider == "fixture:make_tea"


def test_the_prompt_never_asks_a_model_to_describe_the_person():
    prompt = routine_builder._DRAFT_PROMPT
    assert "Never describe or identify the person" in prompt
    assert "only a JSON object" in prompt
    assert routine_builder._video_prompt("tea").endswith("They also said: tea")


# -------------------------------------------------------------- keeping a routine


def _graph(task_id: str = "feed_the_cat") -> dict:
    return {
        "id": task_id,
        "title": "Feed the cat",
        "steps": [
            {"id": "get_the_bowl", "label": "Get the bowl", "objects": ["cup"]},
            {
                "id": "fill_it",
                "label": "Fill it",
                "deps": ["get_the_bowl"],
                "objects": ["water_jug"],
            },
        ],
    }


def test_a_saved_routine_is_still_there_in_a_new_store(tmp_path):
    first = RoutineStore(tmp_path)
    first.save(Routine(id="feed_the_cat", title="Feed the cat", graph=_graph(), source="video"))

    second = RoutineStore(tmp_path)
    kept = second.get("feed_the_cat")
    assert kept is not None
    assert kept.title == "Feed the cat"
    assert kept.source == "video"
    assert parse_task_data(kept.graph).step_ids == ("get_the_bowl", "fill_it")


def test_a_store_with_no_directory_keeps_nothing_on_disk(tmp_path):
    store = RoutineStore(None)
    store.save(Routine(id="feed_the_cat", title="Feed the cat", graph=_graph()))

    assert store.get("feed_the_cat") is not None
    assert list(tmp_path.iterdir()) == []


def test_a_file_that_is_not_a_routine_is_skipped_rather_than_breaking_the_list(tmp_path):
    RoutineStore(tmp_path).save(Routine(id="feed_the_cat", title="Feed the cat", graph=_graph()))
    (tmp_path / "half-written.json").write_text('{"id": "x"}', encoding="utf-8")
    (tmp_path / "rubbish.json").write_text("not json", encoding="utf-8")

    assert [routine.id for routine in RoutineStore(tmp_path).list()] == ["feed_the_cat"]


def test_the_store_is_full_rather_than_filling_a_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(routine_builder, "MAX_SAVED_ROUTINES", 2)
    store = RoutineStore(tmp_path)
    for number in range(2):
        store.save(Routine(id=f"r{number}", title=f"R{number}", graph=_graph()))

    with pytest.raises(RoutineBuilderError, match="already holds 2 routines"):
        store.save(Routine(id="r2", title="R2", graph=_graph()))
    # Replacing one that is already there still works.
    assert store.save(Routine(id="r1", title="R1 again", graph=_graph())).title == "R1 again"


def test_a_routine_id_from_a_url_cannot_escape_the_directory(tmp_path):
    store = RoutineStore(tmp_path / "inside")
    store.save(Routine(id="../../escaped", title="Escaped", graph=_graph()))

    assert [path.parent for path in (tmp_path / "inside").glob("*.json")] == [tmp_path / "inside"]
    assert RoutineStore(tmp_path / "inside").get("../../escaped") is not None


def test_the_built_in_routines_are_the_task_files():
    built_in = {routine.id: routine for routine in built_in_routines()}

    assert set(built_in) == {"tea", "meds"}
    assert built_in["tea"].title == "Make tea"
    assert built_in["tea"].built_in
    assert parse_task_data(built_in["tea"].graph).id == "make_tea"


# ----------------------------------------------------------------------- the routes


def test_drafting_from_a_description_answers_with_a_graph_and_what_it_cost(client):
    response = client.post(
        "/routines/draft", data={"description": "I put bread in the toaster"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["title"] == "Make toast"
    assert body["draft"]["source"] == "text"
    assert body["draft"]["provider"] == "fixture:make_toast"
    assert body["needs_training"] == ["bread", "toaster", "plate", "butter", "knife"]
    assert body["warnings"]
    assert parse_task_data(body["task_graph"]).id == "make_toast"


def test_drafting_a_routine_the_detector_already_knows_needs_no_training(client):
    body = client.post("/routines/draft", data={"description": "make tea"}).json()

    assert body["needs_training"] == []
    assert body["warnings"] == []


def test_a_setup_clip_without_consent_is_refused_without_being_read(client):
    stub = StubDrafter(_answer(_step("Get a cup")))
    use_drafter(stub)

    response = client.post(
        "/routines/draft", files={"video": ("setup.mp4", BIG_CLIP, "video/mp4")}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == CONSENT_REQUIRED
    assert stub.video_calls == []


def test_a_setup_clip_with_consent_is_drafted_from(client):
    stub = StubDrafter(_answer(_step("Get the brush", objects=["toothbrush"])))
    use_drafter(stub)

    response = client.post(
        "/routines/draft",
        data={"consent": "true", "duration_s": "12.5"},
        files={"video": ("setup.mp4", SMALL_CLIP, "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json()["draft"]["source"] == "video"
    assert response.json()["needs_training"] == ["toothbrush"]
    assert stub.video_calls == [(len(SMALL_CLIP), "video/mp4", None)]


def test_a_setup_clip_leaves_nothing_behind_anywhere(client, tmp_path, monkeypatch):
    """SPEC section 12: the clip is held in memory, or in a temp file deleted straight
    after. Nothing new may appear under the repo, the data directories or the temp
    directory, and the bytes may not be in any file that is there."""
    spool = tmp_path / "spool"
    spool.mkdir()
    # Starlette spools an upload over a megabyte to tempfile's directory; point that
    # at somewhere this test can look inside afterwards.
    monkeypatch.setattr(tempfile, "tempdir", str(spool))

    roots = [
        repo_root() / "pipeline" / "src",
        repo_root() / "pipeline" / "tests",
        repo_root() / "tests",
        repo_root() / ".data",
        repo_root() / ".cache",
        tmp_path,
    ]
    before = _files(roots)

    response = client.post(
        "/routines/draft",
        data={"consent": "true", "description": "this is me brushing my teeth"},
        files={"video": ("setup.mp4", BIG_CLIP, "video/mp4")},
    )
    assert response.status_code == 200

    assert _files(roots) == before, "drafting from a clip wrote something down"
    assert list(spool.iterdir()) == [], "the spooled upload was not deleted"
    holding = [path for path in before if CLIP_MARKER in path.read_bytes()]
    assert holding == [], f"the clip itself is in {holding}"


def _files(roots: list[Path]) -> set[Path]:
    """Every file under `roots`, skipping what a test run churns on its own."""
    skip = {"__pycache__", ".pytest_cache", ".venv", "node_modules", ".git", ".ruff_cache"}
    found: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if skip.isdisjoint(path.parts) and path.is_file():
                found.add(path)
    return found


def test_a_setup_clip_bigger_than_one_setup_step_is_refused(client):
    stub = StubDrafter(_answer(_step("Get a cup")))
    use_drafter(stub)

    response = client.post(
        "/routines/draft",
        data={"consent": "true"},
        files={"video": ("setup.mp4", b"\x00" * (MAX_VIDEO_BYTES + 1), "video/mp4")},
    )

    assert response.status_code == 413
    assert "20 MB" in response.json()["detail"]
    assert stub.video_calls == []


def test_a_setup_clip_longer_than_a_minute_is_refused(client):
    response = client.post(
        "/routines/draft",
        data={"consent": "true", "duration_s": "180"},
        files={"video": ("setup.mp4", SMALL_CLIP, "video/mp4")},
    )

    assert response.status_code == 413
    assert "60 seconds" in response.json()["detail"]


def test_an_empty_upload_is_refused(client):
    response = client.post(
        "/routines/draft",
        data={"consent": "true"},
        files={"video": ("setup.mp4", b"", "video/mp4")},
    )

    assert response.status_code == 422
    assert "empty" in response.json()["detail"]


def test_nothing_to_draft_from_is_refused(client):
    assert client.post("/routines/draft", data={}).status_code == 400
    assert client.post("/routines/draft", data={"description": "  "}).status_code == 400


def test_a_draft_the_model_mangled_says_what_was_wrong(client):
    use_drafter(StubDrafter({"steps": [{"objects": ["cup"]}]}))

    response = client.post("/routines/draft", data={"description": "make tea"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "not a routine this can read" in detail
    assert "label" in detail


def test_a_model_that_cannot_be_reached_is_a_502(client):
    class Broken:
        def draft_text(self, description):
            raise httpx2.ConnectError("no route to host")

        def draft_video(self, video, mime, description=None):
            raise httpx2.ConnectError("no route to host")

    use_drafter(Broken())
    response = client.post("/routines/draft", data={"description": "make tea"})

    assert response.status_code == 502
    assert "could not be reached" in response.json()["detail"]


def test_a_reviewed_routine_is_kept_listed_and_fetched(client, tmp_path):
    draft = client.post("/routines/draft", data={"description": "brush my teeth"}).json()

    saved = client.post(
        "/routines",
        json={
            "task_graph": draft["task_graph"],
            "needs_training": draft["needs_training"],
            "source": "text",
        },
    )
    assert saved.status_code == 201
    assert saved.json()["id"] == "brush_your_teeth"
    assert saved.json()["built_in"] is False
    assert saved.json()["step_count"] == 7
    assert saved.json()["needs_training"] == ["toothbrush", "toothpaste", "tap"]

    listed = client.get("/routines").json()
    assert [row["id"] for row in listed] == ["tea", "meds", "brush_your_teeth"]
    assert [row["built_in"] for row in listed] == [True, True, False]

    fetched = client.get("/routines/brush_your_teeth")
    assert fetched.status_code == 200
    assert fetched.json() == saved.json()
    assert (tmp_path / "routines" / "brush_your_teeth.json").is_file()


def test_a_built_in_routine_is_fetched_with_its_graph(client):
    body = client.get("/routines/tea").json()

    assert body["built_in"] is True
    assert body["title"] == "Make tea"
    assert body["task_id"] == "make_tea"
    assert parse_task_data(body["task_graph"]).step_ids[0] == "fill_kettle"


def test_an_unknown_routine_is_a_404(client):
    assert client.get("/routines/nothing_like_this").status_code == 404


def test_saving_something_that_is_not_a_task_graph_is_refused(client):
    for graph in [
        {},
        {"id": "x", "title": "X"},
        {"id": "Not Snake", "title": "X", "steps": [{"id": "a", "label": "A", "objects": ["cup"]}]},
        {"id": "x", "title": "X", "steps": [{"id": "a", "label": "A", "objects": ["sofa"]}]},
        {
            "id": "x",
            "title": "X",
            "steps": [
                {"id": "a", "label": "A", "deps": ["b"], "objects": ["cup"]},
                {"id": "b", "label": "B", "deps": ["a"], "objects": ["cup"]},
            ],
        },
    ]:
        response = client.post("/routines", json={"task_graph": graph})
        assert response.status_code == 422, graph
        assert "not a usable task graph" in response.json()["detail"]


def test_saving_a_routine_that_would_shadow_a_built_in_one_is_refused(client):
    response = client.post("/routines", json={"task_graph": _graph(task_id="tea")})

    assert response.status_code == 409
    assert "built-in" in response.json()["detail"]


def test_a_second_save_replaces_the_first(client):
    client.post("/routines", json={"task_graph": _graph()})
    changed = {**_graph(), "title": "Feed the cat, properly"}
    assert client.post("/routines", json={"task_graph": changed}).status_code == 201

    listed = [row for row in client.get("/routines").json() if not row["built_in"]]
    assert [row["title"] for row in listed] == ["Feed the cat, properly"]


def test_the_saved_routines_are_read_back_off_disk_by_a_new_process(client, tmp_path):
    client.post("/routines", json={"task_graph": _graph()})
    use_routine_store(None)  # as a restart would

    assert [row["id"] for row in client.get("/routines").json() if not row["built_in"]] == [
        "feed_the_cat"
    ]


def test_an_unexpected_field_on_a_save_is_refused(client):
    response = client.post("/routines", json={"task_graph": _graph(), "owner": "me"})
    assert response.status_code == 422


def test_a_drafted_routine_can_be_saved_and_loaded_as_a_task_graph(client):
    """The point of the feature: what the builder produces is what the error
    classifier and the task map already read."""
    draft = client.post("/routines/draft", data={"description": "make me some tea"}).json()
    client.post("/routines", json={"task_graph": draft["task_graph"]})

    graph = parse_task_data(client.get("/routines/make_a_cup_of_tea").json()["task_graph"])
    assert graph.required_steps == (
        "fill_the_kettle",
        "boil_the_kettle",
        "get_a_mug",
        "put_the_tea_bag_in_the_mug",
        "pour_the_water",
        "stir_it",
        "take_the_tea_bag_out",
    )
    assert graph.is_valid_order(list(graph.required_steps))
    assert graph.allowed_objects("stir_it") == frozenset({"spoon", "cup"})


def test_the_loader_reads_a_graph_as_data_the_same_way_it_reads_a_file():
    """`parse_task_data` is `parse_task` without the YAML, and must refuse the same
    things: the builder leans on that instead of round-tripping through YAML text."""
    with pytest.raises(TaskGraphError, match="not snake_case"):
        parse_task_data(_graph(task_id="Feed The Cat"))
    with pytest.raises(TaskGraphError):
        parse_task_data("- not a mapping")

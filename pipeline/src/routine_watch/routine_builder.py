"""Draft a new routine from words or one setup clip (SPEC sections 7 and 12).

Making tea is one task graph; medication is another. Both were written by hand as
`tasks/<name>.yaml`, and everything downstream - the task map, the step recogniser,
the error classifier, the session score - reads nothing but that file. So a person or
their supervisor can have a routine of their own for the price of one more graph, and
this module is the two ways of getting one without writing YAML::

    draft = draft_from_text("I brush my teeth after breakfast")   # Claude, or offline
    draft = draft_from_video(clip, "video/mp4")                   # Gemini watches it once
    graph = to_task_graph(draft)                                  # tasks/tea.yaml's shape

A model drafts; this module decides. The draft is the model's own words, and nothing
in it is trusted: step ids are slugged, a dependency is kept only where it names a
step already placed, objects are mapped onto the classes the detector was actually
trained on, and the result is handed to `tasks/graph.py`'s own loader
(`parse_task_data`) before anybody sees it. `build_routine` also says what it had to
change (`warnings`) and which everyday objects the detector would still have to be
trained on (`needs_training`), so a person reviews a routine they can see the limits
of rather than one that quietly watches the wrong thing.

Every step is also asked what it *is* - one of `routine_watch.actions`' primitives
(`pour`, `put_into`, `shake`, ...) - and that is what makes a built routine one the
step recogniser can actually see happen rather than a list of labels. The prompt names
the primitives straight out of `actions.PRIMITIVES`, and a step whose action is not one
of them, or is about a thing the detector has never been trained on, loses it and says
so.

**Setup clips are a one-time, opt-in step (SPEC section 12).** A clip is held in
memory, capped at `MAX_VIDEO_BYTES` and `MAX_VIDEO_SECONDS` because one setup
demonstration is all it is for, sent to Gemini once, and dropped. Nothing here writes
it anywhere - `cached_call` is keyed on a hash of the clip, never its bytes, exactly
as `verifier.py` does with frames - and no clip ever reaches `REPLAY_DIR`,
`CAMERA_RECORD` or a log. Daily monitoring is unchanged: skeletons, boxes and
timestamps only.

**Offline by default (AGENTS.md).** `get_drafter()` is `FixtureDrafter` - canned
drafts from `pipeline/tests/fixtures/routine_builder/`, picked by keyword - unless
`LIVE_API=1` and a key is configured, so the offline try-out link, CI, the tester and
every test draft a routine without a paid call. `GEMINI_MODEL` and `ANTHROPIC_MODEL`
pick the model; the defaults are the cheapest that work.

`RoutineStore` keeps the routines somebody reviewed: in this process, and as one JSON
file per routine under `ROUTINES_DIR` so a routine built during a demo is still there
after a restart. `api_routines.py` is the HTTP surface over all of it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import quote

import httpx2
import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator

from . import actions
from .api_cache import cached_call, live_api_enabled
from .contracts import ObjectLabel, repo_root
from .explain_claude import DEFAULT_MODEL as DEFAULT_ANTHROPIC_MODEL
from .tasks.graph import TASKS_DIR, TaskGraphError, load_task, parse_task_data
from .verifier import DEFAULT_GEMINI_MODEL

#: One setup clip has to fit in a single Gemini request, inline.
MAX_VIDEO_BYTES = 20 * 1024 * 1024

#: A setup step is one short demonstration, not a recording session (SPEC section 12).
MAX_VIDEO_SECONDS = 60.0

#: Long enough for anybody's routine; short enough that a pasted essay is refused.
MAX_DESCRIPTION_CHARS = 2000

#: More steps than this is a mangled draft, not a routine somebody will review.
MAX_STEPS = 24

#: How long a slugged task or step id may get before it is cut at a word.
MAX_ID_CHARS = 40

#: Container types Gemini reads. A clip the browser cannot name is taken as MP4.
ALLOWED_VIDEO_MIME = frozenset(
    {
        "video/mp4",
        "video/mpeg",
        "video/quicktime",
        "video/webm",
        "video/x-matroska",
        "video/x-msvideo",
        "video/3gpp",
    }
)

#: What `api_routines.py` assumes when an upload arrives without a content type.
DEFAULT_VIDEO_MIME = "video/mp4"

#: Canned drafts for the offline path: one JSON file per routine.
FIXTURES_DIR = repo_root() / "pipeline" / "tests" / "fixtures" / "routine_builder"

#: Which canned draft a clip with no caption stands in for offline.
DEFAULT_CLIP_FIXTURE = "brush_teeth"

#: Where saved routines are kept unless `ROUTINES_DIR` says otherwise.
DEFAULT_ROUTINES_DIR = Path(".data/routines")

#: A public try-out link should not be able to fill a disk one routine at a time.
MAX_SAVED_ROUTINES = 100

#: What a routine was drafted from.
DraftSource = Literal["text", "video"]

#: The classes the running detector reports (SPEC section 6.1), as plain strings.
_DETECTOR_CLASSES = frozenset(str(label) for label in ObjectLabel)

#: Everyday names for a class the detector already knows, so a draft that says "mug"
#: or "tea bag" maps onto `cup` and `teabag` instead of asking for a training run.
#: Keys are slugged, so "tea bag", "Tea Bag" and "tea_bag" all land here.
_SYNONYMS = {
    "mug": "cup",
    "teacup": "cup",
    "tea_cup": "cup",
    "beaker": "cup",
    "tea_bag": "teabag",
    "tea_bags": "teabag",
    "teaspoon": "spoon",
    "tea_spoon": "spoon",
    "dessert_spoon": "spoon",
    "stirrer": "spoon",
    "tumbler": "glass",
    "water_glass": "glass",
    "drinking_glass": "glass",
    "jug": "water_jug",
    "water_jug": "water_jug",
    "pitcher": "water_jug",
    "carafe": "water_jug",
    "dosette_box": "pill_organiser",
    "pill_box": "pill_organiser",
    "pillbox": "pill_organiser",
    "blister_pack": "pill_organiser",
    "weekly_organiser": "pill_organiser",
    "medicine_bottle": "pill_bottle",
    "pill_pot": "pill_bottle",
    "tablet_bottle": "pill_bottle",
    "milk_carton": "milk",
    "milk_jug": "milk",
    "milk_bottle": "milk",
    "sugar_bowl": "sugar",
    "sugar_packet": "sugar",
    "sugar_sachet": "sugar",
    "electric_kettle": "kettle",
    "hands": "hand",
}

#: Task ids, step ids and object names are snake_case (`tasks/graph.py`).
_NOT_SNAKE = re.compile(r"[^a-z0-9]+")


class RoutineBuilderError(ValueError):
    """A draft could not be read, or could not be turned into a usable routine.

    `api_routines.py` answers this with a 422 and the message in it, so the person
    reading it is told what to change rather than that something went wrong.
    """


class ClipRejected(RoutineBuilderError):
    """The setup clip is outside what one setup step accepts: too big, or too long."""


# -------------------------------------------------------------------- what a model said


class _ActionDraft(BaseModel):
    """What the model said the step *is*: one of `routine_watch.actions`' primitives.

    Read as loosely as the rest of a draft. `"action": "pour"` is a type with nothing
    else said, the target may be spelled whichever way reads best, and the type is only
    held to the primitive list later, in `build_routine`, so a model that invents an
    action is told which ones there are rather than having its whole draft refused.
    """

    model_config = ConfigDict(extra="ignore")

    type: str = ""
    object: list[str] = Field(default_factory=list)
    target: str | None = Field(
        default=None, validation_alias=AliasChoices("target", "into", "in", "from")
    )
    seconds: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _a_bare_name_is_a_type(cls, data: object) -> object:
        """`"action": "pour"` meant `{"type": "pour"}`, and `"object": "mug"` a list."""
        if isinstance(data, str):
            return {"type": data}
        if isinstance(data, dict) and isinstance(data.get("object"), str):
            return {**data, "object": [data["object"]]}
        return data


class _StepDraft(BaseModel):
    """One `steps:` entry of a model's answer, read as loosely as is still safe.

    Unknown keys are ignored (a model that volunteers `duration_s` has still answered
    the question), `deps` and `dependencies` are taken as `depends_on`, and a single
    name where a list was asked for is read as a list of one - all of which a model
    does often enough that refusing the whole draft over it would be the wrong call.
    Anything else is a `RoutineBuilderError` the person can act on.
    """

    model_config = ConfigDict(extra="ignore")

    label: str = Field(min_length=1, max_length=120)
    objects: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("depends_on", "deps", "dependencies"),
    )
    optional: bool = False
    once_only: bool = True
    action: _ActionDraft | None = None

    @model_validator(mode="before")
    @classmethod
    def _one_name_is_a_list(cls, data: object) -> object:
        """`"objects": "mug"` meant `["mug"]`."""
        if not isinstance(data, dict):
            return data
        listish = ("objects", "depends_on", "deps", "dependencies")
        return {
            key: [value] if key in listish and isinstance(value, str) else value
            for key, value in data.items()
        }


class _RoutineDraftIn(BaseModel):
    """A whole answer. The title is optional: the prompt asks for one, but a draft
    without it is still a routine, and the description it came from names it."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(default="", max_length=120)
    steps: list[_StepDraft] = Field(min_length=1, max_length=MAX_STEPS)
    notes: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class DraftAction:
    """What the model said one step is, still in its own words and words only."""

    type: str
    objects: tuple[str, ...] = ()
    target: str | None = None
    seconds: float | None = None

    def as_dict(self) -> dict:
        action: dict = {"type": self.type, "object": list(self.objects)}
        if self.target is not None:
            action["target"] = self.target
        if self.seconds is not None:
            action["seconds"] = self.seconds
        return action


@dataclass(frozen=True)
class DraftStep:
    """One step of a drafted routine, still in the model's own words."""

    label: str
    objects: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    optional: bool = False
    once_only: bool = True
    #: Which of `routine_watch.actions`' primitives the model said this step is, if it
    #: said one. `build_routine` is what holds it to the list.
    action: DraftAction | None = None

    def as_dict(self) -> dict:
        drafted = {
            "label": self.label,
            "objects": list(self.objects),
            "depends_on": list(self.depends_on),
            "optional": self.optional,
            "once_only": self.once_only,
        }
        if self.action is not None:
            drafted["action"] = self.action.as_dict()
        return drafted


@dataclass(frozen=True)
class RoutineDraft:
    """What a model made of a description or one setup clip, before anybody reviews it.

    `provider` names who answered (`fixture:make_toast`, `gemini:...`,
    `anthropic:...`) so the screen can be honest about an offline draft, and `notes`
    carries anything the provider wants said alongside it.
    """

    title: str
    steps: tuple[DraftStep, ...]
    source: DraftSource
    provider: str
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "steps": [step.as_dict() for step in self.steps],
            "source": self.source,
            "provider": self.provider,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class BuiltRoutine:
    """A draft turned into a routine: the graph, and what that cost.

    `warnings` is every change the draft had to be held to - a dependency that named
    no earlier step, a step whose objects the detector has never seen - in the words
    the review screen shows. `needs_training` is the everyday objects that are not
    detector classes yet, kept in the draft's own spelling so a person recognises
    them.
    """

    graph: dict
    needs_training: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# ------------------------------------------------------------------------- the drafters


@dataclass(frozen=True)
class DrafterAnswer:
    """What a drafter came back with: the model's own JSON, and who answered.

    `payload` is deliberately untyped - a dict when the provider parsed the JSON
    itself, the raw reply when it did not, and anything at all when the model
    ignored the question.
    """

    payload: object
    provider: str
    notes: tuple[str, ...] = ()


class Drafter(Protocol):
    """Whatever drafts a routine: the offline fixtures, Claude, or Gemini."""

    def draft_text(self, description: str) -> DrafterAnswer:
        """A routine drafted from somebody's own words."""
        ...

    def draft_video(
        self, video: bytes, mime: str, description: str | None = None
    ) -> DrafterAnswer:
        """A routine drafted from one setup clip, with the caption as context."""
        ...


@dataclass(frozen=True)
class _Canned:
    """One file under `FIXTURES_DIR`."""

    name: str
    keywords: tuple[str, ...]
    default: bool
    answer: dict

    @property
    def title(self) -> str:
        return str(self.answer.get("title") or self.name)


@dataclass
class FixtureDrafter:
    """The default drafter: canned answers, no network, nothing paid (AGENTS.md).

    One JSON file per routine under `directory`, each `{"keywords": [...], "answer":
    {...}}` where `answer` is exactly the shape a real model is asked for - so the
    offline path and the real providers go through the same parser, and a new canned
    routine is a new file and no code change.

    A description picks the file whose keywords it hits most often. A description that
    hits nothing picks the file marked `"default": true` and says so in the draft's
    notes: the offline try-out link has to answer something, but it must not pretend
    it read the words it was given.
    """

    directory: Path = FIXTURES_DIR
    #: Which canned routine a clip with no caption stands in for.
    clip: str = DEFAULT_CLIP_FIXTURE

    def draft_text(self, description: str) -> DrafterAnswer:
        return self._pick(description)

    def draft_video(
        self, video: bytes, mime: str, description: str | None = None
    ) -> DrafterAnswer:
        """The clip is taken and dropped: offline there is nothing to read it with,
        which is also all the privacy rule ever wants done with it."""
        if description and description.strip():
            return self._pick(description)
        return DrafterAnswer(
            payload=dict(self._named(self.clip).answer),
            provider=f"fixture:{self.clip}",
            notes=(
                "Drafted offline from a built-in example: the clip was not sent "
                "anywhere. Set LIVE_API=1 to have Gemini read your own clip.",
            ),
        )

    def _pick(self, description: str) -> DrafterAnswer:
        canned = self._all()
        ranked = sorted(canned, key=lambda entry: (-_keyword_hits(description, entry), entry.name))
        best = ranked[0]
        if _keyword_hits(description, best) > 0:
            return DrafterAnswer(payload=dict(best.answer), provider=f"fixture:{best.name}")
        fallback = next((entry for entry in ranked if entry.default), best)
        return DrafterAnswer(
            payload=dict(fallback.answer),
            provider=f"fixture:{fallback.name}",
            notes=(
                f'Drafted offline from the built-in "{fallback.title}" example: '
                "nothing in this description matched one. Set LIVE_API=1 to draft "
                "from your own words.",
            ),
        )

    def _all(self) -> list[_Canned]:
        canned = [_read_canned(path) for path in sorted(self.directory.glob("*.json"))]
        if not canned:
            raise RoutineBuilderError(f"no canned routine drafts in {self.directory}")
        return canned

    def _named(self, name: str) -> _Canned:
        for entry in self._all():
            if entry.name == name:
                return entry
        raise RoutineBuilderError(f"no canned routine draft called {name!r}")


def _read_canned(path: Path) -> _Canned:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        answer = data["answer"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RoutineBuilderError(f"{path.name} is not a canned routine draft: {exc}") from exc
    return _Canned(
        name=path.stem,
        keywords=tuple(str(word) for word in data.get("keywords", ())),
        default=bool(data.get("default")),
        answer=answer if isinstance(answer, dict) else {},
    )


def _keyword_hits(description: str, canned: _Canned) -> int:
    """How many of `canned`'s keywords `description` uses, as whole words.

    Whole words, so "my team" is not a hit for tea and "teeth" is not one either.
    """
    text = (description or "").lower()
    return sum(
        1 for word in canned.keywords if re.search(rf"\b{re.escape(word.lower())}\b", text)
    )


#: The actions a step may be, straight out of `routine_watch.actions`, so the prompt
#: cannot drift from what the recogniser can actually watch for.
_ACTION_CHOICES = "; ".join(
    f"{primitive.name} ({primitive.summary})" for primitive in actions.PRIMITIVES.values()
)

#: What every provider is asked for. JSON only, in everyday words, and never a word
#: about the person: a routine is a list of actions, not a description of who did them.
_DRAFT_PROMPT = (
    "Somebody wants one of their everyday routines watched, step by step, so that a "
    "change in how they do it can be flagged for their family to review. Break the "
    "routine into the fewest steps that can each be seen happening. Answer with only "
    "a JSON object and no other text:\n"
    '{"title": a short name for the routine, "steps": [{'
    '"label": what the person does, in plain words, '
    '"objects": the things they touch, as everyday names, '
    '"depends_on": the labels of the steps that must happen before this one, '
    '"optional": true if skipping it is fine, '
    '"once_only": false if doing it again is normal, '
    '"action": {"type": which action below the step is, '
    '"object": the thing in their hands, '
    '"target": the thing it is done to, where the action has one, '
    '"seconds": how long, for hold only}}]}\n'
    f"The actions are: {_ACTION_CHOICES}. Give every step the one that fits it best, "
    "and leave `action` out of a step that is none of them.\n"
    "List the steps in the order they are usually done. Put a step in depends_on only "
    "if it really has to come first, and only if it is earlier in your own list. At "
    f"most {MAX_STEPS} steps. Never describe or identify the person, their face, their "
    "clothes or their home."
)

_VIDEO_PROMPT = (
    _DRAFT_PROMPT + "\n\nThe video is one person showing the routine once, filmed as a "
    "one-off setup step. Read the steps off what they do with their hands and the "
    "objects they touch."
)


# The prompt holds a literal JSON object, so these are concatenated and never
# `str.format`-ed: a `{` in the example would be read as a field name.
def _text_prompt(description: str) -> str:
    return _DRAFT_PROMPT + f"\n\nThe routine, in their own words: {description.strip()}"


def _video_prompt(description: str | None) -> str:
    caption = (description or "").strip()
    if not caption:
        return _VIDEO_PROMPT
    return _VIDEO_PROMPT + f"\n\nThey also said: {caption}"


class GeminiDrafter:
    """Gemini drafts a routine, from words or from one setup clip.

    The clip goes inline in a single request, which is why `MAX_VIDEO_BYTES` exists,
    and only a hash of it goes into the cache key - so `.cache/api/` holds Gemini's
    JSON answer and never a frame, exactly as `verifier.py` does. `transport` is the
    one seam tests use (`httpx2.MockTransport`), so no test here reaches the network.
    """

    #: Reading a clip takes longer than reading eight frames.
    VIDEO_TIMEOUT_S = 90.0
    TEXT_TIMEOUT_S = 30.0

    _API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        *,
        transport: httpx2.BaseTransport | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self._transport = transport
        self._cache_dir = cache_dir

    def draft_text(self, description: str) -> DrafterAnswer:
        request = {"model": self._model, "kind": "text", "description": description}
        parts = [{"text": _text_prompt(description)}]
        response = cached_call(
            "gemini_routine",
            request,
            lambda: self._call(parts, self.TEXT_TIMEOUT_S),
            self._cache_dir,
        )
        return DrafterAnswer(payload=_gemini_text(response), provider=f"gemini:{self._model}")

    def draft_video(
        self, video: bytes, mime: str, description: str | None = None
    ) -> DrafterAnswer:
        request = {
            "model": self._model,
            "kind": "video",
            "mime": mime,
            "bytes": len(video),
            # Only a hash of the clip goes into the cache key; the bytes never do.
            "clip": hashlib.sha256(video).hexdigest(),
            "description": (description or "").strip(),
        }
        parts = [
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(video).decode()}},
            {"text": _video_prompt(description)},
        ]
        response = cached_call(
            "gemini_routine",
            request,
            lambda: self._call(parts, self.VIDEO_TIMEOUT_S),
            self._cache_dir,
        )
        return DrafterAnswer(payload=_gemini_text(response), provider=f"gemini:{self._model}")

    def _call(self, parts: list[dict], timeout_s: float) -> dict:
        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        # Left to propagate: a timeout or a refusal must never be cached as if it
        # were Gemini's answer (`verifier.py` takes the same line).
        with httpx2.Client(transport=self._transport, timeout=timeout_s) as client:
            reply = client.post(
                f"{self._API_BASE}/models/{self._model}:generateContent",
                json=body,
                headers={"x-goog-api-key": self._api_key},
            )
            reply.raise_for_status()
        return reply.json()


def _gemini_text(response: dict) -> str:
    """The text of Gemini's first candidate, or a `RoutineBuilderError` saying there
    was none (a blocked or empty answer is not a draft)."""
    try:
        return str(response["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError) as exc:
        raise RoutineBuilderError("the model did not answer with a routine") from exc


class ClaudeDrafter:
    """Claude drafts a routine from somebody's own words.

    `client` is anything with `.messages.create(model=, max_tokens=, messages=)`
    returning an object with `.content[0].text` - the shape of `anthropic.Anthropic()`
    and the same seam `explain_claude.py` takes, so tests pass a fake and nothing is
    built until a draft is actually asked for.
    """

    def __init__(
        self,
        client: object | None = None,
        model: str | None = None,
        *,
        cache_dir: Path | None = None,
    ) -> None:
        self._client = client
        self._model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        self._cache_dir = cache_dir

    def draft_text(self, description: str) -> DrafterAnswer:
        prompt = _text_prompt(description)
        request = {"model": self._model, "kind": "text", "prompt": prompt}

        def call() -> dict:
            client = self._client if self._client is not None else _anthropic_client()
            reply = client.messages.create(
                model=self._model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"text": reply.content[0].text}

        result = cached_call("anthropic_routine", request, call, self._cache_dir)
        return DrafterAnswer(payload=result["text"], provider=f"anthropic:{self._model}")

    def draft_video(
        self, video: bytes, mime: str, description: str | None = None
    ) -> DrafterAnswer:
        """Not Claude's job: a setup clip goes to Gemini (`GeminiDrafter`)."""
        raise RoutineBuilderError(
            "drafting from a setup clip needs GEMINI_API_KEY; describe the routine "
            "in words instead"
        )


def _anthropic_client() -> object:
    import anthropic  # only imported for a real, live call

    return anthropic.Anthropic()


@dataclass
class LiveDrafter:
    """The real thing: words to Claude, a setup clip to Gemini.

    Only ever built by `get_drafter()`, and only with `LIVE_API=1`. A kind of request
    there is no key for falls back to `FixtureDrafter` rather than failing, so a
    half-configured `.env` still drafts something from words; a clip with no
    `GEMINI_API_KEY` is refused outright, because there is nothing honest to answer
    with and the clip must not sit around waiting for one.
    """

    fallback: Drafter = field(default_factory=FixtureDrafter)

    def draft_text(self, description: str) -> DrafterAnswer:
        if os.environ.get("ANTHROPIC_API_KEY"):
            return ClaudeDrafter().draft_text(description)
        if os.environ.get("GEMINI_API_KEY"):
            return GeminiDrafter(api_key=os.environ["GEMINI_API_KEY"]).draft_text(description)
        return self.fallback.draft_text(description)

    def draft_video(
        self, video: bytes, mime: str, description: str | None = None
    ) -> DrafterAnswer:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RoutineBuilderError(
                "drafting from a setup clip needs GEMINI_API_KEY; describe the "
                "routine in words instead"
            )
        return GeminiDrafter(api_key=api_key).draft_video(video, mime, description)


#: The drafter this process uses, when something has asked for a specific one.
_drafter: Drafter | None = None


def get_drafter() -> Drafter:
    """The drafter the API should use.

    `FixtureDrafter` unless `LIVE_API=1` (AGENTS.md: no paid call is ever a side
    effect of running tests, CI, the offline demo or the tester).
    """
    if _drafter is not None:
        return _drafter
    if live_api_enabled():
        return LiveDrafter()
    return FixtureDrafter()


def use_drafter(drafter: Drafter | None) -> None:
    """Point this process at `drafter` (or, with None, back at `get_drafter`'s own
    choice). The seam tests use; nothing else should need it."""
    global _drafter
    _drafter = drafter


# ------------------------------------------------------------------------ drafting


def draft_from_text(description: str, drafter: Drafter | None = None) -> RoutineDraft:
    """Draft a routine from somebody's own words.

    Raises `RoutineBuilderError` for an empty or oversized description, and for an
    answer that is not a routine this can read - `api_routines.py` answers that with
    a 422 and the reason in it.
    """
    text = (description or "").strip()
    if not text:
        raise RoutineBuilderError("describe the routine in a sentence or two")
    if len(text) > MAX_DESCRIPTION_CHARS:
        raise RoutineBuilderError(
            f"keep the description under {MAX_DESCRIPTION_CHARS} characters"
        )
    answer = (drafter or get_drafter()).draft_text(text)
    return _draft_of(answer, source="text", named_after=text)


def draft_from_video(
    video: bytes,
    mime: str = DEFAULT_VIDEO_MIME,
    *,
    description: str | None = None,
    duration_s: float | None = None,
    drafter: Drafter | None = None,
) -> RoutineDraft:
    """Draft a routine from one setup clip, held in memory and never written down.

    Consent is the caller's to take before a single byte is read (SPEC section 12);
    `api_routines.py` is where that happens. `duration_s` is what the uploader said
    the clip runs for - a browser knows it from the `<video>` element - and is
    checked when it is given; the byte cap holds either way.

    Raises `ClipRejected` for a clip outside what one setup step accepts, and
    `RoutineBuilderError` for an answer that is not a routine.
    """
    if not video:
        raise RoutineBuilderError("the setup clip is empty")
    if len(video) > MAX_VIDEO_BYTES:
        raise ClipRejected(
            f"one setup clip is at most {MAX_VIDEO_BYTES // (1024 * 1024)} MB; "
            "film a shorter one"
        )
    if duration_s is not None and duration_s > MAX_VIDEO_SECONDS:
        raise ClipRejected(
            f"one setup clip is at most {int(MAX_VIDEO_SECONDS)} seconds; "
            "film a shorter one"
        )
    if mime not in ALLOWED_VIDEO_MIME:
        raise ClipRejected(f"{mime} is not a video this can read")
    answer = (drafter or get_drafter()).draft_video(video, mime, description)
    return _draft_of(answer, source="video", named_after=description or "")


def _draft_of(answer: DrafterAnswer, *, source: DraftSource, named_after: str) -> RoutineDraft:
    """One provider's answer, read into a `RoutineDraft` or refused with the reason."""
    payload = _loads(answer.payload) if isinstance(answer.payload, str) else answer.payload
    try:
        spec = _RoutineDraftIn.model_validate(payload)
    except ValidationError as exc:
        raise RoutineBuilderError(
            f"the draft was not a routine this can read ({_first_problem(exc)})"
        ) from exc
    return RoutineDraft(
        title=spec.title.strip() or _title_from(named_after),
        steps=tuple(
            DraftStep(
                label=step.label.strip(),
                objects=tuple(step.objects),
                depends_on=tuple(step.depends_on),
                optional=step.optional,
                once_only=step.once_only,
                action=_action_draft(step.action),
            )
            for step in spec.steps
        ),
        source=source,
        provider=answer.provider,
        notes=(*answer.notes, *spec.notes),
    )


def _action_draft(spec: _ActionDraft | None) -> DraftAction | None:
    """A model's `action`, kept in its own words; `build_routine` holds it to the list."""
    if spec is None or not spec.type.strip():
        return None
    return DraftAction(
        type=spec.type.strip(),
        objects=tuple(spec.object),
        target=(spec.target or "").strip() or None,
        seconds=spec.seconds,
    )


def _loads(text: str) -> object:
    """JSON out of a model's reply: fenced, wrapped in a sentence, or neither."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", stripped).strip()
    if not stripped.startswith(("{", "[")):
        start, end = stripped.find("{"), stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
    try:
        return json.loads(stripped)
    except ValueError as exc:
        raise RoutineBuilderError(f"the draft was not JSON ({exc})") from exc


def _first_problem(exc: ValidationError) -> str:
    """One readable line out of a pydantic complaint, for a person to act on."""
    problems = exc.errors()
    if not problems:
        return "it had no steps"
    first = problems[0]
    where = ".".join(str(part) for part in first.get("loc", ()))
    if not where:
        # A complaint about the whole answer names the model class that refused it,
        # which means nothing to the person reading the 422.
        return "it was not a JSON object with a list of steps in it"
    return f"{where}: {first.get('msg', 'is not what was asked for')}"


def _title_from(text: str) -> str:
    """A routine's name out of the words it was asked for, when no model gave one."""
    words = " ".join((text or "").split())[:60].strip(" .,;:")
    if not words:
        return "New routine"
    return words[0].upper() + words[1:]


# -------------------------------------------------------------- draft -> task graph


def slug(text: str, limit: int = MAX_ID_CHARS) -> str:
    """`text` as a snake_case id `tasks/graph.py` accepts: `"Get a mug!"` -> `get_a_mug`.

    Accents are folded rather than dropped, so "Café au lait" is `cafe_au_lait` and
    not `caf_au_lait`; an id that would not start with a letter is prefixed, because
    the loader's rule is `[a-z][a-z0-9_]*` and nothing here may hand it anything else;
    and a long one is cut at a word, so a whole sentence of a step label still reads
    as words rather than ending mid-way through one.
    """
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    words = [word for word in _NOT_SNAKE.sub("_", folded.lower()).split("_") if word]
    kept: list[str] = []
    length = 0
    for word in words:
        if kept and length + len(word) + 1 > limit:
            break
        length += len(word) + (1 if kept else 0)
        kept.append(word)
    cleaned = "_".join(kept)[:limit].strip("_")
    if not cleaned:
        return ""
    return cleaned if cleaned[0].isalpha() else f"step_{cleaned}"


def detector_class(name: str) -> str | None:
    """The detector class `name` means, or None if nothing it was trained on matches.

    The class's own name, one of the everyday names in `_SYNONYMS`, or either of
    those in the plural.
    """
    key = slug(name)
    for candidate in (key, key[:-1] if key.endswith("s") else key):
        if candidate in _DETECTOR_CLASSES:
            return candidate
        if candidate in _SYNONYMS:
            return _SYNONYMS[candidate]
    return None


@dataclass(frozen=True)
class _Placed:
    """A step this routine already has, so a later one may depend on it."""

    id: str
    label: str
    optional: bool


def build_routine(draft: RoutineDraft) -> BuiltRoutine:
    """`draft` as a task graph, plus what holding it to the loader's rules cost.

    Nothing in the draft is trusted. Step ids are slugged off the labels and made
    unique; a dependency is kept only where it names a step already placed, and never
    where it would leave a required step waiting on an optional one; objects are
    mapped onto detector classes, and a step with none left watches the hands instead;
    and a step's action is kept only where it is one of `routine_watch.actions`'
    primitives, done with things the detector knows. The graph is then handed to
    `tasks/graph.py`'s own loader before it is returned, so a routine that reaches the
    rest of the pipeline has passed exactly the checks `tasks/tea.yaml` passed.
    """
    warnings: list[str] = []
    needs_training: dict[str, None] = {}
    placed: list[_Placed] = []
    steps: list[dict] = []

    for step in draft.steps:
        step_id = _unique_id(step.label, placed, warnings)
        objects, action = _watched(step, step_id, needs_training, warnings)
        built = {
            "id": step_id,
            "label": step.label,
            "deps": _deps_of(step, step_id, placed, warnings),
            "objects": objects,
            "optional": step.optional,
            "once_only": step.once_only,
        }
        if action is not None:
            built["action"] = action
        steps.append(built)
        placed.append(_Placed(id=step_id, label=step.label, optional=step.optional))

    graph = {
        "id": slug(draft.title) or "new_routine",
        "title": draft.title.strip() or "New routine",
        "steps": steps,
    }
    try:
        parse_task_data(graph, source=f"the drafted routine {graph['id']!r}")
    except TaskGraphError as exc:
        raise RoutineBuilderError(f"the draft is not a usable routine: {exc}") from exc
    return BuiltRoutine(
        graph=graph,
        needs_training=tuple(needs_training),
        warnings=tuple(warnings),
    )


def to_task_graph(draft: RoutineDraft) -> dict:
    """`draft` as a task graph in `tasks/tea.yaml`'s shape, ready to save.

    `build_routine` is this plus what it had to change; use that where a person is
    going to review the result.
    """
    return build_routine(draft).graph


def _unique_id(label: str, placed: Iterable[_Placed], warnings: list[str]) -> str:
    """A step id off `label` that no earlier step of this routine already has."""
    taken = {item.id for item in placed}
    base = slug(label) or "step"
    if base not in taken:
        return base
    for number in count(2):
        candidate = f"{base}_{number}"
        if candidate not in taken:
            warnings.append(
                f'two steps are both called "{label}"; the second one is "{candidate}"'
            )
            return candidate
    raise AssertionError("unreachable")  # pragma: no cover


def _deps_of(
    step: DraftStep, step_id: str, placed: list[_Placed], warnings: list[str]
) -> list[str]:
    """`step`'s dependencies, kept only where they name a step already placed.

    A model happily invents a dependency on a step it never listed, names one that
    comes later, or names the step itself. The loader would refuse the whole graph
    for any of those, so they are dropped and said out loud instead. A required step
    is also never left waiting on an optional one - skipping the optional step would
    otherwise make it impossible, which would read as an omission nobody could avoid
    (`tasks/graph.py` refuses that too).
    """
    by_name: dict[str, _Placed] = {}
    for item in placed:
        by_name.setdefault(item.id, item)
        by_name.setdefault(slug(item.label), item)

    deps: list[str] = []
    for raw in step.depends_on:
        found = by_name.get(slug(raw))
        if found is None:
            warnings.append(
                f'{step_id}: dropped "{raw}" - no earlier step of this routine is called that'
            )
            continue
        if found.optional and not step.optional:
            warnings.append(
                f'{step_id}: dropped "{raw}" - a required step cannot wait on an optional one'
            )
            continue
        if found.id not in deps:
            deps.append(found.id)
    return deps


def _watched(
    step: DraftStep, step_id: str, needs_training: dict[str, None], warnings: list[str]
) -> tuple[list[str], dict | None]:
    """How `step` is to be watched: the detector classes, and the action to look for.

    Everything the detector does not know yet is collected into `needs_training` in
    the draft's own words. A step with nothing left watches the hands, which every
    task shares: the step map still shows it and the recogniser still times it, and
    the review screen is told why.

    The action is kept only where `routine_watch.actions` has it and the things it
    names are things the detector knows - otherwise there is nothing for the
    recogniser to look for, and a step with no action is exactly that. A model that
    *got the action wrong* is said out loud; a thing the detector has simply never been
    trained on is not, because `needs_training` already says so.
    """
    primitive = _primitive_of(step, step_id, warnings)
    named = list(step.objects)
    if primitive is not None and step.action is not None:
        named += [*step.action.objects, *filter(None, (step.action.target,))]

    known: list[str] = []
    for name in named:
        label = detector_class(name)
        if label is None:
            if name.strip():
                needs_training.setdefault(" ".join(name.split()), None)
        elif label not in known:
            known.append(label)
    if not known:
        warnings.append(
            f"{step_id}: nothing the detector knows yet, so it watches the hands"
        )
        return [str(ObjectLabel.HAND)], None
    if primitive is None or step.action is None:
        return known, None
    return known, _action_of(primitive, step.action, known)


def _primitive_of(
    step: DraftStep, step_id: str, warnings: list[str]
) -> actions.Primitive | None:
    """The primitive `step`'s drafted action names, or None with a reason said out loud.

    The type is slugged first, so a model answering "Put into" or "bring to face" is
    taken at its word rather than refused over its capitals.
    """
    drafted = step.action
    if drafted is None:
        return None
    primitive = actions.primitive(slug(drafted.type))
    if primitive is None:
        warnings.append(
            f'{step_id}: dropped the action "{drafted.type}" - a step can be watched '
            f"for one of: {', '.join(actions.ACTION_TYPES)}"
        )
        return None
    if primitive.target and not drafted.target:
        warnings.append(
            f'{step_id}: dropped the "{primitive.name}" action - it needs something '
            "to be done to, and the draft named none"
        )
        return None
    return primitive


def _action_of(
    primitive: actions.Primitive, drafted: DraftAction, known: list[str]
) -> dict | None:
    """One drafted action as a task file's `action:`, or None if it cannot be watched."""
    target = detector_class(drafted.target) if drafted.target else None
    objects = list(
        dict.fromkeys(
            label for name in drafted.objects if (label := detector_class(name)) in known
        )
    )
    if not objects:
        # `"action": "shake"` named the action and left the rest to the step, which is
        # the one place the thing in the hand can come from: whichever of the step's own
        # objects it turns out to be.
        objects = [label for label in known if label != target]
    if not objects or (primitive.target and target not in known):
        return None
    action: dict = {"type": primitive.name, "object": objects}
    if primitive.target:
        action["target"] = target
    if primitive.seconds and drafted.seconds:
        action["seconds"] = float(drafted.seconds)
    return action


# --------------------------------------------------------------- the saved routines


@dataclass(frozen=True)
class Routine:
    """A routine the app can watch: one of the built-in ones, or one somebody built.

    `graph` is the task graph itself, in `tasks/tea.yaml`'s shape, which is the whole
    of a routine as far as the rest of the pipeline is concerned.
    """

    id: str
    title: str
    graph: dict
    needs_training: tuple[str, ...] = ()
    #: What it came from: "built_in" for a `tasks/<name>.yaml`, else "text" or "video".
    source: str = "text"

    @property
    def built_in(self) -> bool:
        return self.source == "built_in"

    def summary(self) -> dict:
        """One row of `GET /routines`: enough to list and pick a routine."""
        return {
            "id": self.id,
            "title": self.title,
            "task_id": str(self.graph.get("id", self.id)),
            "built_in": self.built_in,
            "source": self.source,
            "step_count": len(self.graph.get("steps", ())),
            "needs_training": list(self.needs_training),
        }

    def detail(self) -> dict:
        """One routine in full: its summary plus the graph itself."""
        return {**self.summary(), "task_graph": self.graph}

    def as_json(self) -> dict:
        """What `RoutineStore` writes to disk."""
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "needs_training": list(self.needs_training),
            "task_graph": self.graph,
        }

    @classmethod
    def from_json(cls, data: object) -> Routine:
        """One routine back off disk, or a `RoutineBuilderError` if the file is not one."""
        try:
            return cls(
                id=str(data["id"]),  # type: ignore[index]
                title=str(data["title"]),  # type: ignore[index]
                graph=dict(data["task_graph"]),  # type: ignore[index]
                needs_training=tuple(str(name) for name in data.get("needs_training", ())),  # type: ignore[union-attr]
                source=str(data.get("source", "text")),  # type: ignore[union-attr]
            )
        except (TypeError, KeyError, ValueError) as exc:
            raise RoutineBuilderError(f"not a saved routine: {exc}") from exc


def built_in_routines() -> list[Routine]:
    """Every routine that ships as data: one `tasks/<name>.yaml` each.

    Addressed by file name (`tea`, `meds`), which is also what `tasks.load_task`
    takes, so a routine id is the same thing on both sides.
    """
    routines = []
    for path in sorted(TASKS_DIR.glob("*.yaml")):
        graph = load_task(path.stem)  # cached, and refuses a file that is not a graph
        routines.append(
            Routine(
                id=path.stem,
                title=graph.title,
                graph=yaml.safe_load(path.read_text(encoding="utf-8")),
                source="built_in",
            )
        )
    return routines


class RoutineStore:
    """The routines somebody reviewed and kept: in this process, and on disk.

    One JSON file per routine under `directory`, so a routine built during a demo is
    still there after a restart. `directory=None` keeps them in this process only,
    which is what a test gets unless it asks otherwise. Files are written whole and
    moved into place, so a library is never read half-written, and a file that is not
    a routine is skipped rather than breaking the list it is in.
    """

    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory) if directory is not None else None
        self._routines: dict[str, Routine] = {}
        self._loaded = self.directory is None

    def save(self, routine: Routine) -> Routine:
        """Keep `routine`, replacing one with the same id."""
        self._load()
        if routine.id not in self._routines and len(self._routines) >= MAX_SAVED_ROUTINES:
            raise RoutineBuilderError(
                f"this library already holds {MAX_SAVED_ROUTINES} routines; "
                "delete one before adding another"
            )
        self._routines[routine.id] = routine
        if self.directory is not None:
            self._write(routine)
        return routine

    def get(self, routine_id: str) -> Routine | None:
        self._load()
        return self._routines.get(routine_id)

    def list(self) -> list[Routine]:
        """Every kept routine, by title, so a list reads the same way twice."""
        self._load()
        return sorted(self._routines.values(), key=lambda routine: (routine.title, routine.id))

    def reset(self) -> None:
        """Forget every kept routine in this process. Leaves the files alone."""
        self._routines.clear()
        self._loaded = self.directory is None

    def _path(self, routine_id: str) -> Path:
        """One routine's file. The id reaches this from a URL, so it is
        percent-encoded into a single flat name: nothing it holds escapes
        `directory` (`replays.py` takes the same precaution)."""
        assert self.directory is not None
        return self.directory / (quote(routine_id, safe="") + ".json")

    def _write(self, routine: Routine) -> None:
        assert self.directory is not None
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(routine.id)
        partial = path.with_suffix(".part")
        partial.write_text(json.dumps(routine.as_json(), indent=2) + "\n", encoding="utf-8")
        partial.replace(path)

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.directory is None or not self.directory.is_dir():
            return
        for path in sorted(self.directory.glob("*.json")):
            try:
                routine = Routine.from_json(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, RoutineBuilderError):
                continue  # not a routine, or half of one: skip it, don't break the list
            self._routines.setdefault(routine.id, routine)


def routines_dir() -> Path:
    """Where saved routines are kept: `ROUTINES_DIR`, or `DEFAULT_ROUTINES_DIR`."""
    return Path(os.environ.get("ROUTINES_DIR", "").strip() or DEFAULT_ROUTINES_DIR)


#: The one store this process uses, built on first use so `ROUTINES_DIR` is read then
#: rather than at import time.
_store: RoutineStore | None = None


def get_routine_store() -> RoutineStore:
    """The shared `RoutineStore` for this process."""
    global _store
    if _store is None:
        _store = RoutineStore(routines_dir())
    return _store


def use_routine_store(store: RoutineStore | None) -> None:
    """Point this process at `store` (or, with None, at one built fresh on the next
    call, reading `ROUTINES_DIR` again). The seam tests use."""
    global _store
    _store = store

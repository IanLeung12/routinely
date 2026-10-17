"""The routine builder's routes (SPEC sections 7 and 12).

`POST /routines/draft` takes a description or one setup clip and answers with the
drafted routine, the task graph it turns into, what the detector would still have to
be trained on and everything the draft had to be held to. `POST /routines` keeps a
graph somebody has reviewed; `GET /routines[/{id}]` lists the built-in routines
(`tasks/<name>.yaml`) and the kept ones together. `routine_builder.py` does the work.

**A setup clip never lands anywhere (SPEC section 12).** Consent is checked before a
single byte is read, so an un-consented clip is refused unread. The upload is then
read in bounded chunks into memory and the `UploadFile` is closed in a `finally`,
which deletes the temp file Starlette spools it to above a megabyte - in the operating
system's temp directory, never in the repo. Nothing here writes to `REPLAY_DIR`,
`CAMERA_RECORD`, `ROUTINES_DIR` or anywhere else, and no clip, byte count or file name
is logged. Daily monitoring is untouched: skeletons, boxes and timestamps only.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from . import routine_builder
from .routine_builder import ClipRejected, Routine, RoutineBuilderError
from .tasks.graph import TaskGraphError, parse_task_data

logger = logging.getLogger(__name__)

router = APIRouter()

#: Said once, so the route and its test cannot drift apart.
CONSENT_REQUIRED = (
    "a setup clip needs consent=true: this is a one-time, opt-in step, and the clip "
    "is only sent to the model that reads it"
)

NOTHING_TO_DRAFT_FROM = "describe the routine in words, or upload one setup clip"

MODEL_UNREACHABLE = "the drafting model could not be reached; try again"

#: How much of an upload is read at a time, so a huge one is refused rather than
#: buffered whole.
_CHUNK_BYTES = 256 * 1024


class RoutineIn(BaseModel):
    """A reviewed routine, as the builder screen sends it back to be kept.

    `task_graph` is checked by `tasks/graph.py`'s own loader before anything is kept,
    so an edited graph is held to the same rules as a drafted one.
    """

    model_config = ConfigDict(extra="forbid")

    task_graph: dict
    #: The everyday objects the draft named that the detector does not know yet, kept
    #: alongside the routine as a note for whoever reviews it.
    needs_training: list[str] = Field(default_factory=list, max_length=40)
    source: Literal["text", "video"] = "text"


@router.post("/routines/draft")
async def draft_routine(
    description: Annotated[str | None, Form()] = None,
    consent: Annotated[bool, Form()] = False,
    duration_s: Annotated[float | None, Form()] = None,
    video: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """Draft a routine from `description`, or from one setup `video` with `consent`.

    400 with nothing to draft from, and 400 for a clip without consent (checked
    before the clip is read at all). 413 for a clip bigger than
    `routine_builder.MAX_VIDEO_BYTES` or longer than `MAX_VIDEO_SECONDS`. 422 when
    the model's answer is not a routine, with the reason in it. Offline the draft
    comes from a canned example and says so in `draft.notes`.
    """
    if video is None and not (description or "").strip():
        raise HTTPException(status_code=400, detail=NOTHING_TO_DRAFT_FROM)
    if video is not None and not consent:
        # Checked first: an un-consented clip is refused without being read.
        raise HTTPException(status_code=400, detail=CONSENT_REQUIRED)

    try:
        if video is None:
            draft = routine_builder.draft_from_text(description or "")
        else:
            draft = await _draft_from_upload(video, description, duration_s)
        built = routine_builder.build_routine(draft)
    except ClipRejected as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except RoutineBuilderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Only the exception's type is logged: a provider's message could carry the
        # request back with it, and nothing about a clip is ever written down.
        logger.warning("routine draft failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=MODEL_UNREACHABLE) from exc

    return {
        "draft": draft.as_dict(),
        "task_graph": built.graph,
        "needs_training": list(built.needs_training),
        "warnings": list(built.warnings),
    }


async def _draft_from_upload(
    video: UploadFile, description: str | None, duration_s: float | None
) -> routine_builder.RoutineDraft:
    """Read the clip, draft from it, and drop it, whatever happens.

    `video.close()` deletes the temp file Starlette spooled the upload to if it was
    big enough to be spooled at all, and the bytes themselves go out of scope here
    (SPEC section 12).
    """
    clip = b""
    try:
        clip = await _read_capped(video, routine_builder.MAX_VIDEO_BYTES)
        return routine_builder.draft_from_video(
            clip,
            video.content_type or routine_builder.DEFAULT_VIDEO_MIME,
            description=description,
            duration_s=duration_s,
        )
    finally:
        await video.close()
        del clip


async def _read_capped(video: UploadFile, limit: int) -> bytes:
    """The whole upload, or `ClipRejected` as soon as it goes over `limit`.

    Read in chunks rather than whole, so a clip far bigger than one setup step is
    refused instead of held in memory first.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await video.read(_CHUNK_BYTES):
        total += len(chunk)
        if total > limit:
            raise ClipRejected(
                f"one setup clip is at most {limit // (1024 * 1024)} MB; film a shorter one"
            )
        chunks.append(chunk)
    if not total:
        raise RoutineBuilderError("the setup clip is empty")
    return b"".join(chunks)


@router.post("/routines", status_code=201)
def save_routine(body: RoutineIn) -> dict:
    """Keep a routine somebody has reviewed, and answer with it as `GET` would.

    422 if the graph is not one `tasks/graph.py` would load, and 409 if it would
    shadow a built-in routine or the library is full.
    """
    try:
        graph = parse_task_data(body.task_graph, source="the routine being saved")
    except TaskGraphError as exc:
        raise HTTPException(
            status_code=422, detail=f"this is not a usable task graph: {exc}"
        ) from exc

    if any(existing.id == graph.id for existing in routine_builder.built_in_routines()):
        raise HTTPException(status_code=409, detail=f"{graph.id!r} is a built-in routine")

    routine = Routine(
        id=graph.id,
        title=graph.title,
        graph=body.task_graph,
        needs_training=tuple(body.needs_training),
        source=body.source,
    )
    try:
        saved = routine_builder.get_routine_store().save(routine)
    except RoutineBuilderError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return saved.detail()


@router.get("/routines")
def list_routines() -> list[dict]:
    """Every routine the app can watch: the built-in ones, then the kept ones."""
    built_in = sorted(routine_builder.built_in_routines(), key=lambda item: item.title)
    saved = routine_builder.get_routine_store().list()
    return [routine.summary() for routine in (*built_in, *saved)]


@router.get("/routines/{routine_id}")
def get_routine(routine_id: str) -> dict:
    """One routine in full, built-in or kept, with its task graph."""
    for routine in routine_builder.built_in_routines():
        if routine.id == routine_id:
            return routine.detail()
    saved = routine_builder.get_routine_store().get(routine_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="routine not found")
    return saved.detail()

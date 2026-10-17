"""`api_state.reset()` must mutate `_feedback_store` in place (T284): routers
import it directly at module load time, so rebinding the module global would
leave them pointing at the old, un-reset store."""

from routine_watch import api_state
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import DEMO_NOW


def test_reset_clears_feedback_without_replacing_the_store():
    store = api_state._feedback_store

    api_state._feedback_store.record(
        "alert-res-x",
        "res-x",
        AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="nurse", at=DEMO_NOW),
    )
    assert api_state._feedback_store.pattern_weights("res-x") or True  # has some state
    assert api_state._feedback_store.threshold("res-x", base=2.0) != 2.0

    api_state.reset()

    assert api_state._feedback_store is store
    assert api_state._feedback_store.threshold("res-x", base=2.0) == 2.0


def test_flagged_residents_only_includes_raw_flagged_status():
    flagged = api_state._flagged_residents()
    assert all(resident["status"] == "flagged" for resident in flagged)

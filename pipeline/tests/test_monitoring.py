from routine_watch.monitoring import MonitoringStore, get_monitoring_store


def test_unknown_room_defaults_to_on():
    store = MonitoringStore()
    assert store.is_on("room-1") is True


def test_pause_then_resume():
    store = MonitoringStore()
    store.set("room-1", False)
    assert store.is_on("room-1") is False
    store.set("room-1", True)
    assert store.is_on("room-1") is True


def test_paused_rooms_sorted():
    store = MonitoringStore()
    store.set("room-3", False)
    store.set("room-1", False)
    store.set("room-2", False)
    assert store.paused_rooms() == ["room-1", "room-2", "room-3"]


def test_resuming_removes_from_paused_rooms():
    store = MonitoringStore()
    store.set("room-1", False)
    store.set("room-2", False)
    store.set("room-1", True)
    assert store.paused_rooms() == ["room-2"]


def test_reset_clears_every_pause():
    store = MonitoringStore()
    store.set("room-1", False)
    store.set("room-2", False)
    store.reset()
    assert store.paused_rooms() == []
    assert store.is_on("room-1") is True


def test_get_monitoring_store_returns_shared_instance():
    assert get_monitoring_store() is get_monitoring_store()

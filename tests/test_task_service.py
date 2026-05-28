import pytest

from epdm_sim.services.task_service import TaskService


def test_task_status_lifecycle_and_cache():
    state = {}
    service = TaskService(state)
    result = service.run("x", "h1", lambda: 42)
    assert result == 42
    assert service.get("x").status == "success"
    cached = service.run("x", "h1", lambda: 99)
    assert cached == 42
    assert service.get("x").status == "cached"


def test_failed_task_captures_exception():
    service = TaskService({})
    with pytest.raises(RuntimeError):
        service.run("bad", "h", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert service.get("bad").status == "failed"
    assert "boom" in service.get("bad").error


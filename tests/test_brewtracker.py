"""Focused tests for BrewTracker runtime normalization."""

from custom_components.brewfather.coordinator import BrewfatherCoordinator
from custom_components.brewfather.sensor import BrewfatherSensor, SensorKinds
from custom_components.brewfather.coordinator import BrewfatherCoordinatorData


def _tracker(*, paused=False, completed=False):
    return {
        "_id": "tracker-1",
        "enabled": True,
        "completed": completed,
        "stage": 0,
        "stages": [
            {
                "name": "Mash",
                "step": 0,
                "paused": paused,
                "duration": 600,
                "position": 300,
                "steps": [
                    {"name": "Heat strike water", "active": True},
                    {"name": "Dough-in"},
                ],
            }
        ],
    }


def _data(tracker):
    data = BrewfatherCoordinatorData()
    data.batch_id = "batch-1"
    data.brew_tracker = tracker
    data.brew_tracker_batch_id = "batch-1"
    data.brew_tracker_batch_name = "Test batch"
    data.brew_tracker_recipe_name = "Test recipe"
    data.brew_tracker_batch_status = "Planning"
    return data


def test_tracker_active_contract():
    assert BrewfatherCoordinator._brewtracker_active(_tracker()) is True
    assert BrewfatherCoordinator._brewtracker_active(None) is False
    assert BrewfatherCoordinator._brewtracker_active({"enabled": False, "stages": [{}]}) is False
    assert BrewfatherCoordinator._brewtracker_active({"enabled": True, "stages": []}) is False


def test_status_running_paused_completed_and_inactive():
    assert BrewfatherSensor._status(_tracker()) == "running"
    assert BrewfatherSensor._status(_tracker(paused=True)) == "paused"
    assert BrewfatherSensor._status(_tracker(completed=True)) == "completed"
    assert BrewfatherSensor._status(None) == "inactive"


def test_stage_step_and_next_step_selection():
    tracker = _tracker()
    stage = BrewfatherSensor._stage(tracker)

    assert stage["name"] == "Mash"
    assert BrewfatherSensor._step(stage)["name"] == "Heat strike water"
    assert BrewfatherSensor._next(stage)["name"] == "Dough-in"


def test_paused_remaining_and_progress_are_stable():
    stage = BrewfatherSensor._stage(_tracker(paused=True))

    assert BrewfatherSensor._remaining(stage) == 300
    assert BrewfatherSensor._progress(stage) == 50.0


def test_brewtracker_sensors_expose_expected_states_and_attributes():
    data = _data(_tracker(paused=True))

    status = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_status, None, "test_status"
    )
    stage = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_stage, None, "test_stage"
    )
    step = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_step, None, "test_step"
    )
    next_step = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_next_step, None, "test_next"
    )
    progress = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_progress, None, "test_progress"
    )
    remaining = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_time_remaining, None, "test_remaining"
    )
    raw = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_raw, None, "test_raw"
    )

    assert status.state == "paused"
    assert stage.state == "Mash"
    assert step.state == "Heat strike water"
    assert next_step.state == "Dough-in"
    assert progress.state == 50.0
    assert remaining.state == 300
    assert raw.state == "paused"
    assert raw.extra_state_attributes["data"] == data.brew_tracker
    assert status.extra_state_attributes["brew_tracker_batch_status"] == "Planning"
    assert status.extra_state_attributes["active"] is True


def test_missing_tracker_keeps_status_available_but_other_values_unavailable():
    data = _data(None)

    status = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_status, None, "test_status"
    )
    stage = BrewfatherSensor._refresh_sensor_data(
        data, SensorKinds.brewtracker_stage, None, "test_stage"
    )

    assert status.state == "inactive"
    assert status.attr_available is True
    assert stage.state is None
    assert stage.attr_available is False

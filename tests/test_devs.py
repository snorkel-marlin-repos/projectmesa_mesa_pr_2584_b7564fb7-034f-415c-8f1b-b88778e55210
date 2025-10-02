"""Tests for experimental Simulator classes."""

from unittest.mock import MagicMock, Mock

import pytest

from mesa import Model
from mesa.experimental.devs.eventlist import EventList, Priority, SimulationEvent
from mesa.experimental.devs.simulator import ABMSimulator, DEVSimulator


def test_devs_simulator():
    """Tests devs simulator."""
    simulator = DEVSimulator()

    # setup
    model = MagicMock(spec=Model)
    simulator.setup(model)

    assert len(simulator.event_list) == 0
    assert simulator.model == model
    assert simulator.time == 0

    # schedule_event_now
    fn1 = MagicMock()
    event1 = simulator.schedule_event_now(fn1)
    assert event1 in simulator.event_list
    assert len(simulator.event_list) == 1

    # schedule_event_absolute
    fn2 = MagicMock()
    event2 = simulator.schedule_event_absolute(fn2, 1.0)
    assert event2 in simulator.event_list
    assert len(simulator.event_list) == 2

    # schedule_event_relative
    fn3 = MagicMock()
    event3 = simulator.schedule_event_relative(fn3, 0.5)
    assert event3 in simulator.event_list
    assert len(simulator.event_list) == 3

    # run_for
    simulator.run_for(0.8)
    fn1.assert_called_once()
    fn3.assert_called_once()
    assert simulator.time == 0.8

    simulator.run_for(0.2)
    fn2.assert_called_once()
    assert simulator.time == 1.0

    simulator.run_for(0.2)
    assert simulator.time == 1.2

    with pytest.raises(ValueError):
        simulator.schedule_event_absolute(fn2, 0.5)

    # step
    simulator = DEVSimulator()
    model = MagicMock(spec=Model)
    simulator.setup(model)

    fn = MagicMock()
    simulator.schedule_event_absolute(fn, 1.0)
    simulator.run_next_event()
    fn.assert_called_once()
    assert simulator.time == 1.0
    simulator.run_next_event()
    assert simulator.time == 1.0

    simulator = DEVSimulator()
    with pytest.raises(Exception):
        simulator.run_next_event()

    # cancel_event
    simulator = DEVSimulator()
    model = MagicMock(spec=Model)
    simulator.setup(model)
    fn = MagicMock()
    event = simulator.schedule_event_relative(fn, 0.5)
    simulator.cancel_event(event)
    assert event.CANCELED

    # simulator reset
    simulator.reset()
    assert len(simulator.event_list) == 0
    assert simulator.model is None
    assert simulator.time == 0.0

    # run without setup
    simulator = DEVSimulator()
    with pytest.raises(Exception):
        simulator.run_until(10)

    # setup with time advanced
    simulator = DEVSimulator()
    simulator.time = simulator.start_time + 1
    model = MagicMock(spec=Model)
    with pytest.raises(Exception):
        simulator.setup(model)

    # setup with event scheduled
    simulator = DEVSimulator()
    simulator.schedule_event_now(Mock())
    with pytest.raises(Exception):
        simulator.setup(model)


def test_abm_simulator():
    """Tests abm simulator."""
    simulator = ABMSimulator()

    # setup
    model = MagicMock(spec=Model)
    simulator.setup(model)

    # schedule_event_next_tick
    fn = MagicMock()
    simulator.schedule_event_next_tick(fn)
    assert len(simulator.event_list) == 2

    simulator.run_for(3)
    assert model.step.call_count == 3
    assert simulator.time == 3

    # run without setup
    simulator = ABMSimulator()
    with pytest.raises(Exception):
        simulator.run_until(10)


def test_simulation_event():
    """Tests for SimulationEvent class."""
    some_test_function = MagicMock()

    time = 10
    event = SimulationEvent(
        time,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )

    assert event.time == time
    assert event.fn() is some_test_function
    assert event.function_args == []
    assert event.function_kwargs == {}
    assert event.priority == Priority.DEFAULT

    # execute
    event.execute()
    some_test_function.assert_called_once()

    with pytest.raises(Exception):
        SimulationEvent(
            time, None, priority=Priority.DEFAULT, function_args=[], function_kwargs={}
        )

    # check calling with arguments
    some_test_function = MagicMock()
    event = SimulationEvent(
        time,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=["1"],
        function_kwargs={"x": 2},
    )
    event.execute()
    some_test_function.assert_called_once_with("1", x=2)

    # check if we pass over deletion of callable silently because of weakrefs
    def some_test_function(x, y):
        return x + y

    event = SimulationEvent(time, some_test_function, priority=Priority.DEFAULT)
    del some_test_function
    event.execute()

    # cancel
    some_test_function = MagicMock()
    event = SimulationEvent(
        time,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=["1"],
        function_kwargs={"x": 2},
    )
    event.cancel()
    assert event.fn is None
    assert event.function_args == []
    assert event.function_kwargs == {}
    assert event.priority == Priority.DEFAULT
    assert event.CANCELED

    # comparison for sorting
    event1 = SimulationEvent(
        10,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    event2 = SimulationEvent(
        10,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    assert event1 < event2  # based on just unique_id as tiebraker

    event1 = SimulationEvent(
        11,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    event2 = SimulationEvent(
        10,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    assert event1 > event2

    event1 = SimulationEvent(
        10,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    event2 = SimulationEvent(
        10,
        some_test_function,
        priority=Priority.HIGH,
        function_args=[],
        function_kwargs={},
    )
    assert event1 > event2


def test_eventlist():
    """Tests for EventList."""
    event_list = EventList()

    assert len(event_list._events) == 0
    assert isinstance(event_list._events, list)
    assert event_list.is_empty()

    # add event
    some_test_function = MagicMock()
    event = SimulationEvent(
        1,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    event_list.add_event(event)
    assert len(event_list) == 1
    assert event in event_list

    # remove event
    event_list.remove(event)
    assert len(event_list) == 1
    assert event.CANCELED

    # peak ahead
    event_list = EventList()
    for i in range(10):
        event = SimulationEvent(
            i,
            some_test_function,
            priority=Priority.DEFAULT,
            function_args=[],
            function_kwargs={},
        )
        event_list.add_event(event)
    events = event_list.peak_ahead(2)
    assert len(events) == 2
    assert events[0].time == 0
    assert events[1].time == 1

    events = event_list.peak_ahead(11)
    assert len(events) == 10

    event_list._events[6].cancel()
    events = event_list.peak_ahead(10)
    assert len(events) == 9

    event_list = EventList()
    with pytest.raises(Exception):
        event_list.peak_ahead()

    # pop event
    event_list = EventList()
    for i in range(10):
        event = SimulationEvent(
            i,
            some_test_function,
            priority=Priority.DEFAULT,
            function_args=[],
            function_kwargs={},
        )
        event_list.add_event(event)
    event = event_list.pop_event()
    assert event.time == 0

    event_list = EventList()
    event = SimulationEvent(
        9,
        some_test_function,
        priority=Priority.DEFAULT,
        function_args=[],
        function_kwargs={},
    )
    event_list.add_event(event)
    event.cancel()
    with pytest.raises(Exception):
        event_list.pop_event()

    # clear
    event_list.clear()
    assert len(event_list) == 0

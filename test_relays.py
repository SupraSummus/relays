"""
Basic pytest tests for relay circuit simulation.
Tests are kept small and elegant, focusing on core functionality.
"""

import pytest
from relays import (
    Relay, WireState, RelayPosition,
    HIGH, LOW, FLOATING, SHORT_CIRCUIT,
    propagate_signals, get_unstable_relays, transition_relay,
    inverter_circuit, buffer_with_glitch, race_condition_circuit
)


def test_wire_states():
    """Test basic wire state constants."""
    assert HIGH == WireState.HIGH
    assert LOW == WireState.LOW
    assert FLOATING == WireState.FLOATING
    assert SHORT_CIRCUIT == WireState.SHORT_CIRCUIT


def test_relay_creation():
    """Test relay component creation."""
    relay = Relay(coil_a='A', coil_b='B', comm='C', no='NO', nc='NC', name='Test')
    assert relay.name == 'Test'
    assert relay.coil_a == 'A'
    assert relay.no == 'NO'
    assert relay.nc == 'NC'


def test_propagate_signals_simple():
    """Test signal propagation through a single relay."""
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Relay OFF - connects comm to nc
    relay_states = {relay: RelayPosition.OFF}
    fixed_wires = {'nc': HIGH}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    assert result['comm'] == HIGH
    assert result['nc'] == HIGH


def test_propagate_signals_on_position():
    """Test signal propagation when relay is ON."""
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Relay ON - connects comm to no
    relay_states = {relay: RelayPosition.ON}
    fixed_wires = {'no': LOW}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    assert result['comm'] == LOW
    assert result['no'] == LOW


def test_propagate_signals_switching():
    """Test signal propagation during switching (break-before-make)."""
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Relay SWITCHING - no connections made
    relay_states = {relay: RelayPosition.SWITCHING}
    fixed_wires = {'no': HIGH, 'nc': LOW}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    assert result['comm'] == FLOATING  # Not connected to anything


def test_get_unstable_relays_energized():
    """Test detection of relays that need to switch when energized."""
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no')
    
    # Coil energized (A=HIGH, B=LOW) but relay is OFF
    relay_states = {relay: RelayPosition.OFF}
    wire_states = {'coil_a': HIGH, 'coil_b': LOW}
    
    unstable = get_unstable_relays([relay], relay_states, wire_states)
    assert relay in unstable


@pytest.mark.parametrize(
    ('relay_state', 'coil_a_state', 'coil_b_state', 'expected_unstable'),
    [
        (RelayPosition.OFF, WireState.HIGH, WireState.LOW, True),
        (RelayPosition.OFF, WireState.LOW, WireState.HIGH, True),
        (RelayPosition.SWITCHING, WireState.LOW, WireState.HIGH, True),
        (RelayPosition.SWITCHING, WireState.LOW, WireState.LOW, True),
        (RelayPosition.ON, WireState.HIGH, WireState.LOW, False),
        (RelayPosition.ON, WireState.LOW, WireState.HIGH, False),
        (RelayPosition.ON, WireState.HIGH, WireState.HIGH, True),
        (RelayPosition.ON, WireState.SHORT_CIRCUIT, WireState.LOW, True),
        (RelayPosition.ON, WireState.FLOATING, WireState.HIGH, True),
        (RelayPosition.OFF, WireState.FLOATING, WireState.SHORT_CIRCUIT, False),
    ],
)
def test_get_unstable_relays(relay_state, coil_a_state, coil_b_state, expected_unstable):
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no')
    relay_states = {relay: relay_state}
    wire_states = {'coil_a': coil_a_state, 'coil_b': coil_b_state}
    unstable = get_unstable_relays([relay], relay_states, wire_states)
    assert (relay in unstable) == expected_unstable


def test_transition_relay():
    """Test relay state transition."""
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    initial_states = {relay: RelayPosition.OFF}
    fixed_wires = {'no': HIGH, 'nc': LOW}
    
    new_relay_states, new_wire_states = transition_relay(
        relay, RelayPosition.ON, [relay], initial_states, fixed_wires
    )
    
    assert new_relay_states[relay] == RelayPosition.ON
    assert new_wire_states['comm'] == HIGH  # Connected to no


def test_inverter_circuit_low_input():
    """Test inverter circuit with LOW input."""
    relays = inverter_circuit()
    inputs = {'In': LOW, 'VCC': HIGH, 'GND': LOW}
    
    # With LOW input, relay stays OFF, comm connects to nc (VCC)
    relay_states = {}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == HIGH


def test_inverter_circuit_high_input():
    """Test inverter circuit with HIGH input after stabilization."""
    relays = inverter_circuit()
    inverter_relay = relays[0]
    inputs = {'In': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # With HIGH input, relay should switch ON, comm connects to no (GND)
    relay_states = {inverter_relay: RelayPosition.ON}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == LOW


def test_buffer_glitch_during_switching():
    """Test buffer circuit shows glitch during switching."""
    relays = buffer_with_glitch()
    buffer_relay = relays[0]
    inputs = {'In': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # During switching, output should be floating
    relay_states = {buffer_relay: RelayPosition.SWITCHING}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == FLOATING


def test_race_condition_short_circuit():
    """Test race condition circuit can create short circuits."""
    relays = race_condition_circuit()
    path1_relay = relays[0]
    path2_relay = relays[1]
    inputs = {'Trigger': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # Both relays ON simultaneously - should create short circuit
    relay_states = {path1_relay: RelayPosition.ON, path2_relay: RelayPosition.ON}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == SHORT_CIRCUIT  # Short circuit detected


def test_short_circuit_vs_floating():
    """Test that short circuits are distinguished from floating wires."""
    # Create a simple relay to test floating vs short circuit
    relay = Relay(coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Test floating: relay in switching position with fixed wires
    relay_states = {relay: RelayPosition.SWITCHING}
    fixed_wires = {'no': HIGH, 'nc': LOW}
    result = propagate_signals([relay], relay_states, fixed_wires)
    assert result['comm'] == FLOATING  # Not connected to anything
    
    # Test short circuit: create conflicting signals using race condition circuit
    race_relays = race_condition_circuit()
    path1_relay = race_relays[0]
    path2_relay = race_relays[1]
    inputs = {'Trigger': HIGH, 'VCC': HIGH, 'GND': LOW}
    conflict_states = {path1_relay: RelayPosition.ON, path2_relay: RelayPosition.ON}
    result = propagate_signals(race_relays, conflict_states, inputs)
    assert result['Out'] == SHORT_CIRCUIT  # Actual conflict


def test_circuit_creation_functions():
    """Test circuit creation functions return proper relay configurations."""
    # Test each circuit creation function
    inverter = inverter_circuit()
    assert len(inverter) == 1
    assert inverter[0].name == 'Inverter'
    
    buffer = buffer_with_glitch()
    assert len(buffer) == 1
    assert buffer[0].name == 'Buffer'
    
    race = race_condition_circuit()
    assert len(race) == 2
    assert race[0].name == 'Path1_High'
    assert race[1].name == 'Path2_Low'


def test_relays_without_names():
    """Test that relays can be created and used without names."""
    # Create relays without names
    relay1 = Relay(coil_a='In1', coil_b='GND', comm='Out1', no='VCC', nc='GND')
    relay2 = Relay(coil_a='In2', coil_b='GND', comm='Out2', no='VCC', nc='GND')
    
    # Names should be None
    assert relay1.name is None
    assert relay2.name is None
    
    # They should still work in circuits
    relays = [relay1, relay2]
    inputs = {'In1': HIGH, 'In2': LOW, 'VCC': HIGH, 'GND': LOW}
    
    # Both relays should be identifiable by their object identity
    relay_states = {relay1: RelayPosition.ON, relay2: RelayPosition.OFF}
    result = propagate_signals(relays, relay_states, inputs)
    
    # relay1 should connect comm to no (VCC), relay2 should connect comm to nc (GND)
    assert result['Out1'] == HIGH  # relay1 is ON, connects to VCC
    assert result['Out2'] == LOW   # relay2 is OFF, connects to GND
    
    # Test that unstable relays detection works with unnamed relays
    unstable = get_unstable_relays(relays, {}, inputs)
    assert relay1 in unstable  # Should want to switch to ON
    assert relay2 not in unstable  # Should stay OFF

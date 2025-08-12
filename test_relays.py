"""
Basic pytest tests for relay circuit simulation.
Tests are kept small and elegant, focusing on core functionality.
"""

import pytest
from relays import (
    Relay, WireState, RelayPosition,
    HIGH, LOW, FLOATING,
    propagate_signals, get_unstable_relays, transition_relay,
    inverter_circuit, buffer_with_glitch, race_condition_circuit
)


def test_wire_states():
    """Test basic wire state constants."""
    assert HIGH == WireState.HIGH
    assert LOW == WireState.LOW
    assert FLOATING == WireState.FLOATING


def test_relay_creation():
    """Test relay component creation."""
    relay = Relay(name='Test', coil_a='A', coil_b='B', comm='C', no='NO', nc='NC')
    assert relay.name == 'Test'
    assert relay.coil_a == 'A'
    assert relay.no == 'NO'
    assert relay.nc == 'NC'


def test_propagate_signals_simple():
    """Test signal propagation through a single relay."""
    relay = Relay(name='R1', coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Relay OFF - connects comm to nc
    relay_states = {'R1': RelayPosition.OFF}
    fixed_wires = {'nc': HIGH}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    assert result['comm'] == HIGH
    assert result['nc'] == HIGH


def test_propagate_signals_on_position():
    """Test signal propagation when relay is ON."""
    relay = Relay(name='R1', coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Relay ON - connects comm to no
    relay_states = {'R1': RelayPosition.ON}
    fixed_wires = {'no': LOW}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    assert result['comm'] == LOW
    assert result['no'] == LOW


def test_propagate_signals_switching():
    """Test signal propagation during switching (break-before-make)."""
    relay = Relay(name='R1', coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    # Relay SWITCHING - no connections made
    relay_states = {'R1': RelayPosition.SWITCHING}
    fixed_wires = {'no': HIGH, 'nc': LOW}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    assert result['comm'] == FLOATING  # Not connected to anything


def test_get_unstable_relays_energized():
    """Test detection of relays that need to switch when energized."""
    relay = Relay(name='R1', coil_a='coil_a', coil_b='coil_b', comm='comm', no='no')
    
    # Coil energized (A=HIGH, B=LOW) but relay is OFF
    relay_states = {'R1': RelayPosition.OFF}
    wire_states = {'coil_a': HIGH, 'coil_b': LOW}
    
    unstable = get_unstable_relays([relay], relay_states, wire_states)
    assert 'R1' in unstable


def test_get_unstable_relays_stable():
    """Test stable relay detection."""
    relay = Relay(name='R1', coil_a='coil_a', coil_b='coil_b', comm='comm', no='no')
    
    # Coil not energized and relay is OFF - stable
    relay_states = {'R1': RelayPosition.OFF}
    wire_states = {'coil_a': LOW, 'coil_b': LOW}
    
    unstable = get_unstable_relays([relay], relay_states, wire_states)
    assert 'R1' not in unstable


def test_transition_relay():
    """Test relay state transition."""
    relay = Relay(name='R1', coil_a='coil_a', coil_b='coil_b', comm='comm', no='no', nc='nc')
    
    initial_states = {'R1': RelayPosition.OFF}
    fixed_wires = {'no': HIGH, 'nc': LOW}
    
    new_relay_states, new_wire_states = transition_relay(
        'R1', RelayPosition.ON, [relay], initial_states, fixed_wires
    )
    
    assert new_relay_states['R1'] == RelayPosition.ON
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
    inputs = {'In': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # With HIGH input, relay should switch ON, comm connects to no (GND)
    relay_states = {'Inverter': RelayPosition.ON}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == LOW


def test_buffer_glitch_during_switching():
    """Test buffer circuit shows glitch during switching."""
    relays = buffer_with_glitch()
    inputs = {'In': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # During switching, output should be floating
    relay_states = {'Buffer': RelayPosition.SWITCHING}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == FLOATING


def test_race_condition_short_circuit():
    """Test race condition circuit can create short circuits."""
    relays = race_condition_circuit()
    inputs = {'Trigger': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # Both relays ON simultaneously - should create short circuit
    relay_states = {'Path1_High': RelayPosition.ON, 'Path2_Low': RelayPosition.ON}
    result = propagate_signals(relays, relay_states, inputs)
    
    assert result['Out'] == FLOATING  # Short circuit detected


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
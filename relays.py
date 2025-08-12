"""
Asynchronous Relay Circuit Prover - Component-based approach
Models actual relay components with break-before-make switching
"""

from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Wire states
class WireState(Enum):
    LOW = 0
    HIGH = 1
    FLOATING = None
    
# Constants for readability
HIGH = WireState.HIGH
LOW = WireState.LOW
FLOATING = WireState.FLOATING

# Component definition
@dataclass
class Relay:
    """5-pin relay: 2 coil pins, 1 common, 1 NO, 1 NC"""
    name: str
    coil_a: str      # Coil pin A wire
    coil_b: str      # Coil pin B wire  
    comm: str        # Common pin wire
    no: str          # Normally Open pin wire
    nc: str = None   # Normally Closed pin wire (optional)

# Relay can be in three states during switching
class RelayPosition(Enum):
    OFF = 0        # Connected to NC
    SWITCHING = 1  # Break-before-make: connected to neither
    ON = 2         # Connected to NO

# State is just dictionaries
WireStates = Dict[str, WireState]
RelayStates = Dict[str, RelayPosition]

def propagate_signals(
    relays: List[Relay],
    relay_states: RelayStates,
    fixed_wires: WireStates
) -> WireStates:
    """
    Propagate signals through relay switches using connection groups.
    Relays create bidirectional connections between wires.
    """
    # Start with fixed wires
    wires = dict(fixed_wires)
    
    # Build connection groups - sets of wires that are connected together
    connections = []
    
    for relay in relays:
        pos = relay_states.get(relay.name, RelayPosition.OFF)
        
        if pos == RelayPosition.ON and relay.no:
            # Connect comm and NO
            connections.append({relay.comm, relay.no})
        elif pos == RelayPosition.OFF and relay.nc:
            # Connect comm and NC
            connections.append({relay.comm, relay.nc})
        # If SWITCHING, no connections made
    
    # Merge overlapping connection groups
    merged = True
    while merged:
        merged = False
        new_connections = []
        used = set()
        
        for i, group1 in enumerate(connections):
            if i in used:
                continue
            
            merged_group = set(group1)
            for j, group2 in enumerate(connections):
                if i != j and j not in used and group1 & group2:
                    # Groups share a wire, merge them
                    merged_group |= group2
                    used.add(j)
                    merged = True
            
            new_connections.append(merged_group)
            used.add(i)
        
        connections = new_connections
    
    # Now propagate signals within each connection group
    for group in connections:
        # Find all defined values in this group
        values = []
        for wire in group:
            if wire in fixed_wires:
                values.append(fixed_wires[wire])
            elif wire in wires and wires[wire] != FLOATING:
                values.append(wires[wire])
        
        if values:
            # Check for conflicts (short circuits)
            if len(set(values)) > 1:
                # Multiple different values - this is a short circuit!
                # Mark all wires in group as FLOATING (undefined)
                for wire in group:
                    if wire not in fixed_wires:
                        wires[wire] = FLOATING
            else:
                # All values are the same, propagate to all wires in group
                value = values[0]
                for wire in group:
                    if wire not in fixed_wires:
                        wires[wire] = value
    
    # Mark any undefined wires as floating
    all_wires = set()
    for relay in relays:
        all_wires.update([relay.coil_a, relay.coil_b, relay.comm])
        if relay.no:
            all_wires.add(relay.no)
        if relay.nc:
            all_wires.add(relay.nc)
    
    for wire in all_wires:
        if wire not in wires:
            wires[wire] = FLOATING
    
    return wires

def get_unstable_relays(
    relays: List[Relay],
    relay_states: RelayStates,
    wire_states: WireStates
) -> Set[str]:
    """Find relays that need to change state based on coil voltage"""
    unstable = set()
    
    for relay in relays:
        # Get coil voltage
        coil_a_state = wire_states.get(relay.coil_a, FLOATING)
        coil_b_state = wire_states.get(relay.coil_b, FLOATING)
        
        # Relay energizes when coil_a is HIGH and coil_b is LOW
        coil_energized = (coil_a_state == HIGH and coil_b_state == LOW)
        
        current_pos = relay_states.get(relay.name, RelayPosition.OFF)
        
        # Check if relay needs to change
        if coil_energized and current_pos != RelayPosition.ON:
            unstable.add(relay.name)
        elif not coil_energized and current_pos != RelayPosition.OFF:
            unstable.add(relay.name)
        # Relays in SWITCHING state are always unstable
        elif current_pos == RelayPosition.SWITCHING:
            unstable.add(relay.name)
    
    return unstable

def get_relay_transitions(
    relay_name: str,
    relays: List[Relay],
    relay_states: RelayStates,
    wire_states: WireStates
) -> List[RelayPosition]:
    """
    Get possible next positions for a relay.
    Implements break-before-make: OFF -> SWITCHING -> ON and ON -> SWITCHING -> OFF
    """
    # Find the relay
    relay = next((r for r in relays if r.name == relay_name), None)
    if not relay:
        return []
    
    current_pos = relay_states.get(relay_name, RelayPosition.OFF)
    
    # Get coil state
    coil_a_state = wire_states.get(relay.coil_a, FLOATING)
    coil_b_state = wire_states.get(relay.coil_b, FLOATING)
    coil_energized = (coil_a_state == HIGH and coil_b_state == LOW)
    
    # Determine transitions
    if current_pos == RelayPosition.OFF:
        if coil_energized:
            return [RelayPosition.SWITCHING]  # Start switching
        else:
            return []  # Stay OFF
            
    elif current_pos == RelayPosition.ON:
        if not coil_energized:
            return [RelayPosition.SWITCHING]  # Start switching
        else:
            return []  # Stay ON
            
    elif current_pos == RelayPosition.SWITCHING:
        # Complete the switch
        if coil_energized:
            return [RelayPosition.ON]
        else:
            return [RelayPosition.OFF]
    
    return []

def transition_relay(
    relay_name: str,
    new_position: RelayPosition,
    relays: List[Relay],
    relay_states: RelayStates,
    fixed_wires: WireStates
) -> Tuple[RelayStates, WireStates]:
    """Apply a relay transition and recompute wire states"""
    new_relay_states = {**relay_states, relay_name: new_position}
    new_wire_states = propagate_signals(relays, new_relay_states, fixed_wires)
    return new_relay_states, new_wire_states

def explore_all_sequences(
    relays: List[Relay],
    fixed_wires: WireStates,
    initial_relay_states: RelayStates = None,
    max_depth: int = 100,
    visited: Set[str] = None
) -> List[List[Tuple[RelayStates, WireStates]]]:
    """
    Explore all possible relay switching sequences.
    Returns paths where each state is (relay_states, wire_states).
    """
    if initial_relay_states is None:
        initial_relay_states = {}
    if visited is None:
        visited = set()
    
    # Compute current wire state
    wire_states = propagate_signals(relays, initial_relay_states, fixed_wires)
    current_state = (initial_relay_states, wire_states)
    
    # Create state key for cycle detection
    state_key = str(sorted(initial_relay_states.items()))
    if state_key in visited or max_depth <= 0:
        return [[current_state]]
    
    visited = visited | {state_key}
    
    # Find relays that can transition
    unstable = get_unstable_relays(relays, initial_relay_states, wire_states)
    
    if not unstable:
        return [[current_state]]
    
    # Try each possible transition
    all_paths = []
    for relay_name in unstable:
        transitions = get_relay_transitions(relay_name, relays, initial_relay_states, wire_states)
        
        for new_position in transitions:
            new_relay_states, new_wire_states = transition_relay(
                relay_name, new_position, relays, initial_relay_states, fixed_wires
            )
            
            future_paths = explore_all_sequences(
                relays, fixed_wires, new_relay_states, max_depth - 1, visited
            )
            
            for path in future_paths:
                all_paths.append([current_state] + path)
    
    return all_paths

def simulate(
    relays: List[Relay],
    inputs: Dict[str, WireState],
    max_depth: int = 100
) -> List[List[Tuple[RelayStates, WireStates]]]:
    """Simulate circuit with given inputs"""
    return explore_all_sequences(relays, inputs, max_depth=max_depth)

def wait_for_stable(
    relays: List[Relay],
    inputs: Dict[str, WireState],
    output_wires: List[str]
) -> Tuple[bool, Set[Tuple]]:
    """Check if outputs stabilize and return all possible values"""
    paths = simulate(relays, inputs)
    
    stable_outputs = set()
    all_stable = True
    
    for path in paths:
        final_relay_states, final_wire_states = path[-1]
        
        unstable = get_unstable_relays(relays, final_relay_states, final_wire_states)
        if not unstable:
            output_vals = tuple((w, final_wire_states.get(w, FLOATING)) for w in output_wires)
            stable_outputs.add(output_vals)
        else:
            all_stable = False
    
    return all_stable, stable_outputs

# Example circuits

def inverter_circuit():
    """Simple inverter using one relay
    Output is the common pin, switches between VCC (NC) and GND (NO)"""
    return [
        Relay(name='Inverter', coil_a='In', coil_b='GND', comm='Out', no='GND', nc='VCC')
    ]

def buffer_with_glitch():
    """Buffer that might glitch during switching
    Output is common pin, switches between GND (NC) and VCC (NO)"""
    return [
        Relay(name='Buffer', coil_a='In', coil_b='GND', comm='Out', no='VCC', nc='GND')
    ]

def race_condition_circuit():
    """Two relays racing to set output - one pulls high, one pulls low"""
    return [
        Relay(name='Path1_High', coil_a='Trigger', coil_b='GND', comm='VCC', no='Out'),
        Relay(name='Path2_Low', coil_a='Trigger', coil_b='GND', comm='GND', no='Out'),
    ]

def sr_latch():
    """SR latch - cross-coupled relays"""
    return [
        # Main SR relays
        Relay(name='S_relay', coil_a='S', coil_b='GND', comm='VCC', no='Q'),
        Relay(name='R_relay', coil_a='R', coil_b='GND', comm='VCC', no='Q_bar'),
        # Hold relays for feedback
        Relay(name='Q_hold', coil_a='Q', coil_b='GND', comm='VCC', no='Q'),
        Relay(name='Qbar_hold', coil_a='Q_bar', coil_b='GND', comm='VCC', no='Q_bar'),
    ]

# Test functions

def test_inverter():
    print("Testing Inverter...")
    relays = inverter_circuit()
    
    for input_val in [LOW, HIGH]:
        print(f"\n  Input={input_val.name}:")
        inputs = {'In': input_val, 'VCC': HIGH, 'GND': LOW}
        
        paths = simulate(relays, inputs)
        stable, outputs = wait_for_stable(relays, inputs, ['Out'])
        
        print(f"    Paths: {len(paths)}")
        
        # Show intermediate states
        for path in paths:
            print(f"    Path: ", end="")
            for relay_states, wire_states in path:
                inv_state = relay_states.get('Inverter', RelayPosition.OFF)
                out_state = wire_states.get('Out', FLOATING)
                print(f"[{inv_state.name}, Out={out_state.name}] -> ", end="")
            print("done")
        
        if outputs:
            for out in outputs:
                out_val = dict(out)['Out']
                expected = LOW if input_val == HIGH else HIGH
                print(f"    Final: {out_val.name} (expected {expected.name}) {'✓' if out_val == expected else '✗'}")

def test_glitch_detection():
    print("\nTesting Glitch Detection in Buffer...")
    relays = buffer_with_glitch()
    
    print("  Switching from LOW to HIGH:")
    inputs = {'In': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    paths = simulate(relays, inputs, max_depth=10)
    
    # Check for glitches - output going to FLOATING during switch
    glitch_found = False
    for path in paths:
        for _, wire_states in path:
            if wire_states.get('Out') == FLOATING:
                glitch_found = True
                break
    
    print(f"  Break-before-make glitch detected: {glitch_found} {'✓' if glitch_found else '✗'}")
    
    # Show a path with glitch
    for path in paths[:1]:  # Just show first path
        print("  Example path:")
        for relay_states, wire_states in path:
            buf_state = relay_states.get('Buffer', RelayPosition.OFF)
            out_state = wire_states.get('Out', FLOATING)
            print(f"    Buffer={buf_state.name:10} Out={out_state.name}")

def test_race_condition():
    print("\nTesting Race Condition...")
    relays = race_condition_circuit()
    
    inputs = {'Trigger': HIGH, 'VCC': HIGH, 'GND': LOW}
    paths = simulate(relays, inputs)
    
    stable, outputs = wait_for_stable(relays, inputs, ['Out'])
    
    print(f"  Found {len(paths)} execution paths")
    print(f"  Possible final outputs:")
    for out in outputs:
        out_val = dict(out)['Out']
        print(f"    Out = {out_val.name}")
    
    if len(outputs) > 1:
        print("  ⚠️  RACE CONDITION - output depends on relay timing!")
    
    # Check for short circuits
    short_circuit_found = False
    for path in paths:
        for relay_states, wire_states in path:
            p1 = relay_states.get('Path1_High', RelayPosition.OFF)
            p2 = relay_states.get('Path2_Low', RelayPosition.OFF)
            if p1 == RelayPosition.ON and p2 == RelayPosition.ON:
                out = wire_states.get('Out', FLOATING)
                if out == FLOATING:
                    short_circuit_found = True
    
    if short_circuit_found:
        print("  ⚠️  SHORT CIRCUIT detected when both relays are ON!")
    
    # Show how different paths lead to different results
    print("\n  Sample paths leading to different outputs:")
    shown = set()
    for path in paths:
        final_out = path[-1][1].get('Out', FLOATING)
        if final_out not in shown:
            shown.add(final_out)
            print(f"\n    Path to Out={final_out.name}:")
            for relay_states, wire_states in path[-3:]:  # Show last 3 states
                p1 = relay_states.get('Path1_High', RelayPosition.OFF)
                p2 = relay_states.get('Path2_Low', RelayPosition.OFF)
                out = wire_states.get('Out', FLOATING)
                print(f"      Path1_High={p1.name:10} Path2_Low={p2.name:10} -> Out={out.name}")

if __name__ == "__main__":
    test_inverter()
    test_glitch_detection()
    test_race_condition()

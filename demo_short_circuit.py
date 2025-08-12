#!/usr/bin/env python3
"""
Demonstration of SHORT_CIRCUIT vs FLOATING states.

This script demonstrates how the new SHORT_CIRCUIT state makes actual signal
conflicts stand out clearly, instead of being disguised as floating wires.
"""

from relays import (
    Relay, RelayPosition, HIGH, LOW, FLOATING, SHORT_CIRCUIT,
    propagate_signals, race_condition_circuit
)

def demonstrate_difference():
    """Show the clear difference between FLOATING and SHORT_CIRCUIT states."""
    
    print("=" * 60)
    print("DEMONSTRATION: SHORT_CIRCUIT vs FLOATING")
    print("=" * 60)
    
    print("\n1. FLOATING STATE (normal unconnected wire):")
    print("   - Relay in break-before-make switching position")
    print("   - Common pin temporarily disconnected from both NO and NC")
    
    relay = Relay(name='Switch', coil_a='ctrl', coil_b='gnd', 
                  comm='output', no='vcc', nc='gnd')
    
    # Relay in switching position - creates legitimate floating state
    relay_states = {'Switch': RelayPosition.SWITCHING}
    fixed_wires = {'vcc': HIGH, 'gnd': LOW}
    result = propagate_signals([relay], relay_states, fixed_wires)
    
    print(f"   Result: output = {result['output'].name}")
    print("   ✓ This is normal behavior during relay switching\n")
    
    print("2. SHORT_CIRCUIT STATE (signal conflict):")
    print("   - Two relays simultaneously driving same wire")  
    print("   - One tries to pull HIGH, other tries to pull LOW")
    
    # Use race condition circuit where both relays can drive same output
    race_relays = race_condition_circuit()
    inputs = {'Trigger': HIGH, 'VCC': HIGH, 'GND': LOW}
    
    # Both relays ON simultaneously - creates actual short circuit
    conflict_states = {'Path1_High': RelayPosition.ON, 'Path2_Low': RelayPosition.ON}
    result = propagate_signals(race_relays, conflict_states, inputs)
    
    print(f"   Result: Out = {result['Out'].name}")
    print("   ⚠️  This indicates a hardware fault condition!\n")
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"FLOATING:      {FLOATING.name:<15} - Normal unconnected wire")
    print(f"SHORT_CIRCUIT: {SHORT_CIRCUIT.name:<15} - Hardware conflict/fault")
    print("\n✨ Short circuits now stand out clearly instead of being disguised!")
    print("   This makes debugging relay circuits much easier.")

if __name__ == "__main__":
    demonstrate_difference()
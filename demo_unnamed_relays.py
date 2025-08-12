#!/usr/bin/env python3
"""
Demo script showing that relays no longer require names.
Creates a simple circuit with unnamed relays and simulates it.
"""

from relays import (
    Relay, WireState, RelayPosition,
    HIGH, LOW, FLOATING,
    simulate, wait_for_stable
)

def demo_unnamed_relays():
    """Create and test a circuit with unnamed relays."""
    print("Demo: Relays Without Names")
    print("=" * 40)
    
    # Create a simple inverter relay without specifying a name
    inverter_relay = Relay(
        coil_a='Input',
        coil_b='GND', 
        comm='Output',
        no='GND',      # When energized, connects Output to GND (LOW)
        nc='VCC'       # When not energized, connects Output to VCC (HIGH)
    )
    
    # Verify it has no name
    print(f"Inverter relay name: {inverter_relay.name}")
    print("Circuit: Input -> Inverter -> Output")
    print("Logic: When Input=HIGH, relay energizes and Output=LOW")
    print("       When Input=LOW, relay stays off and Output=HIGH")
    print()
    
    # Create the circuit
    relays = [inverter_relay]
    
    # Test different input combinations
    test_cases = [
        ("LOW input", {'Input': LOW, 'VCC': HIGH, 'GND': LOW}, HIGH),
        ("HIGH input", {'Input': HIGH, 'VCC': HIGH, 'GND': LOW}, LOW),
    ]
    
    for test_name, inputs, expected in test_cases:
        print(f"Testing {test_name}:")
        
        # Simulate the circuit
        stable, outputs = wait_for_stable(relays, inputs, ['Output'])
        
        if stable and outputs:
            final_out = list(outputs)[0]
            final_value = dict(final_out)['Output']
            print(f"  Output: {final_value.name} (expected: {expected.name})")
            
            if final_value == expected:
                print("  ✓ Circuit behaves as expected (inverter)")
            else:
                print("  ✗ Unexpected output")
        else:
            print("  Circuit did not stabilize!")
        
        print()

if __name__ == "__main__":
    demo_unnamed_relays()
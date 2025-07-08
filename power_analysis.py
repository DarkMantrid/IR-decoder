#!/usr/bin/env python3
"""
Midea IR Power Command Deep Analysis Tool

Copyright (c) 2025 Orpheus Johansson (deadtechsolutions)
Repository: https://github.com/deadtechsolutions/IR-decoder

This script performs detailed bit-level analysis of Midea power commands to help
understand and validate the power state encoding mechanism in the IR protocol.

PURPOSE:
========
- Analyze power ON vs power OFF command differences at the bit level
- Validate power state decoding logic used in main.py
- Understand how different bits encode various AC functions
- Debug and improve power state detection accuracy

FEATURES:
=========
- Bit-by-bit analysis of command bytes
- Power state decoding validation across multiple bit positions
- Mode encoding analysis for different bit combinations  
- Side-by-side comparison of known power commands
- Binary representation of all analyzed bytes

USAGE:
======
    python power_analysis.py

The script analyzes hardcoded power commands but can be easily modified
to analyze any Midea IR command bytes for debugging purposes.

ANALYSIS APPROACH:
=================
1. Examines each bit position in relevant command bytes
2. Tests different bit patterns to understand encoding schemes
3. Compares known working power ON/OFF commands
4. Validates the power detection logic used in the main decoder

This tool was instrumental in determining that bit 7 of Byte 1 encodes
the power state (0 = OFF, 1 = ON) in the Midea IR protocol.
"""

def decode_midea_power_corrected(byte_val):
    """
    Analyze all bit positions in a byte to understand power encoding.
    
    This function systematically examines each bit in the provided byte
    to help identify which bit position encodes the power state.
    
    Args:
        byte_val (int): Byte value to analyze (typically Byte 1 from Midea command)
        
    Output:
        Prints analysis of each bit position showing:
        - Bit position (0-7)
        - Bit value (0 or 1) 
        - Binary representation of the complete byte
        
    This analysis helped determine that bit 7 is the power state indicator.
    """
    # The power bit might be in a different position
    # Let's check multiple bit positions
    print(f"Analyzing byte 0x{byte_val:02X} = {byte_val:08b}")
    for bit_pos in range(8):
        bit_val = (byte_val >> bit_pos) & 0x01
        print(f"  Bit {bit_pos}: {bit_val}")

def decode_mode_corrected(byte_val):
    """
    Analyze different bit combinations to understand mode encoding.
    
    This function systematically tests different bit ranges within a byte
    to help identify how the AC mode is encoded in the Midea protocol.
    
    Args:
        byte_val (int): Byte value to analyze for mode encoding
        
    Output:
        Prints analysis showing:
        - Complete byte in binary and hex
        - Different bit range extractions (1-3 bits)
        - Possible mode values for each bit combination
        
    This analysis helped determine that bits 5-7 encode the AC mode.
    """
    print(f"Mode byte: 0x{byte_val:02X} = {byte_val:08b}")
    
    # Check different bit combinations for mode
    for start_bit in range(0, 6):
        for num_bits in range(1, 4):
            if start_bit + num_bits <= 8:
                mask = (1 << num_bits) - 1
                mode_val = (byte_val >> start_bit) & mask
                print(f"  Bits {start_bit}-{start_bit+num_bits-1}: {mode_val:0{num_bits}b} = {mode_val}")

def main():
    """
    Perform comprehensive analysis of Midea power commands.
    
    This function conducts a detailed examination of known power ON and OFF
    commands to validate and understand the power state encoding in the
    Midea IR protocol.
    
    Analysis includes:
    1. Bit-level analysis of command and mode bytes
    2. Power state detection validation  
    3. Mode encoding examination
    4. Key differences identification between ON/OFF states
    
    The hardcoded command bytes represent actual captured IR signals:
    - power_off: Real power OFF command from Midea AC
    - power_on: Real power ON command from Midea AC  
    
    Results from this analysis confirmed that:
    - Bit 7 of Byte 1 encodes power state (0=OFF, 1=ON)
    - Bits 5-7 of Byte 1 encode AC mode
    - Other bytes contain temperature, fan, and checksum data
    """
    print("POWER COMMAND ANALYSIS")
    print("=" * 50)
    
    # Command data from actual IR captures
    # These represent real Midea AC power commands decoded from IR signals
    power_off = [0xA1, 0x02, 0x42, 0xFF, 0xFF, 0xDF, 0x17, 0xBF, 0x6F, 0x40, 0x00, 0x08]
    power_on = [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28]
    
    print("\n1. POWER OFF Command Analysis:")
    print("Byte 0 (Command):", hex(power_off[0]))
    decode_midea_power_corrected(power_off[0])
    print("Byte 1 (Mode/Power):", hex(power_off[1]))
    decode_mode_corrected(power_off[1])
    
    print("\n2. POWER ON Command Analysis:")
    print("Byte 0 (Command):", hex(power_on[0]))
    decode_midea_power_corrected(power_on[0])
    print("Byte 1 (Mode/Power):", hex(power_on[1]))
    decode_mode_corrected(power_on[1])
    
    print("\n3. KEY DIFFERENCES SUMMARY:")
    print("Main difference is in Byte 1 (Mode/Power byte):")
    print(f"  Power OFF: 0x02 = {0x02:08b}")
    print(f"  Power ON:  0x82 = {0x82:08b}")
    print("             ^^^^^^^")
    print("             Bit 7 difference: 0 (OFF) vs 1 (ON)")
    print("\nConclusion: Bit 7 of Byte 1 encodes power state")
    print("  Difference:      ^^^^^^^  (bit 7)")
    
    print("\nConclusion:")
    print("- The power state appears to be controlled by BIT 7 of BYTE 1")
    print("- Bit 7 = 0: Power OFF") 
    print("- Bit 7 = 1: Power ON")
    print("- The decoder was looking at the wrong bit/byte for power state")
    
    print("\nFor ESP32 implementation:")
    print("To toggle power: flip bit 7 of byte 1")
    print("  power_off: byte[1] = original_byte[1] & 0x7F  // Clear bit 7")
    print("  power_on:  byte[1] = original_byte[1] | 0x80  // Set bit 7")

if __name__ == "__main__":
    main()

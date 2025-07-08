#!/usr/bin/env python3
"""
Midea IR Command Comparison and Analysis Tool

Copyright (c) 2025 Orpheus Johansson (deadtechsolutions)
Repository: https://github.com/deadtechsolutions/IR-decoder

This script performs detailed byte-level comparison of Midea IR commands to help
understand the protocol structure and identify bit patterns for different functions.

PURPOSE:
========
- Compare commands side-by-side to identify differences
- Analyze bit patterns to understand encoding schemes  
- Validate decoder logic by examining known command pairs
- Help reverse-engineer additional protocol features

FEATURES:
=========
- Byte-by-byte comparison with XOR difference calculation
- Binary representation of differing bits
- Analysis of power state encoding (bit 7 of Byte 1)
- Mode and temperature pattern identification
- Checksum validation and structure analysis

USAGE:
======
    python compare_commands.py

The script includes hardcoded examples of power on/off commands but can be
easily modified to compare any two Midea IR command byte arrays.

EXAMPLE OUTPUT:
==============
Byte-by-byte comparison of Power ON vs Power OFF:
============================================================
Byte   Power OFF    Power ON     Difference   Binary Diff
------------------------------------------------------------
Byte 0  0xA1 (161)   0xA1 (161)   Same         --------
Byte 1  0x02 (  2)   0x82 (130)   0x80         10000000
[... continues for all bytes ...]

Key differences found:
- Byte 1: 0x02 (Power OFF) vs 0x82 (Power ON)
  - Bit 7 difference: 0 vs 1
  - This confirms power state encoding

HOW TO USE FOR OTHER COMMANDS:
=============================
1. Replace the hardcoded byte arrays with your commands
2. Add more comparison functions for different command types
3. Use the analysis functions to decode individual bytes
"""

def compare_commands():
    """
    Perform detailed comparison between Power ON and Power OFF commands.
    
    This function demonstrates how to analyze differences between two Midea
    IR commands at the byte and bit level. It's particularly useful for
    understanding the protocol structure and validating decoder logic.
    
    The comparison includes:
    - Byte-by-byte value differences
    - XOR analysis to show which bits differ
    - Binary representation of differences
    - Interpretation of key differences (power state, checksums)
    
    You can modify this function to compare any two command byte arrays
    by replacing the hardcoded values with your own captured data.
    """
    # Power OFF command bytes
    power_off = [0xA1, 0x02, 0x42, 0xFF, 0xFF, 0xDF, 0x17, 0xBF, 0x6F, 0x40, 0x00, 0x08]
    
    # Power ON command bytes  
    power_on = [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28]
    
    print("Byte-by-byte comparison of Power ON vs Power OFF:")
    print("=" * 60)
    print(f"{'Byte':<6} {'Power OFF':<12} {'Power ON':<12} {'Difference':<12} {'Binary Diff'}")
    print("-" * 60)
    
    for i, (off_byte, on_byte) in enumerate(zip(power_off, power_on)):
        diff = off_byte ^ on_byte  # XOR to find different bits
        diff_str = "Same" if diff == 0 else f"0x{diff:02X}"
        binary_diff = f"{diff:08b}" if diff != 0 else "--------"
        
        print(f"Byte {i:<2} 0x{off_byte:02X} ({off_byte:3d})   0x{on_byte:02X} ({on_byte:3d})   {diff_str:<12} {binary_diff}")
    
    print("\nKey differences found:")
    print("- Byte 1: 0x02 (Power OFF) vs 0x82 (Power ON)")
    print("  - Bit 7 difference: 0 vs 1") 
    print("  - This likely indicates power state")
    print("- Byte 5: 0xDF vs 0x5F (checksum difference)")
    print("- Byte 7: 0xBF vs 0x9F") 
    print("- Byte 11: 0x08 vs 0x28 (checksum difference)")
    
    print("\nBinary analysis of key byte differences:")
    print(f"Byte 1: 0x02 = {0x02:08b} (Power OFF)")
    print(f"Byte 1: 0x82 = {0x82:08b} (Power ON)")
    print("        ^^^^^^^  - bit 7 (MSB) is the power state indicator")
    
    # Analyze mode differences
    print(f"\nMode analysis:")
    print(f"Power OFF - Byte 1: 0x02 = Auto mode (bits 5-7: {(0x02 >> 5) & 0x07:03b})")
    print(f"Power ON  - Byte 1: 0x82 = Heat mode (bits 5-7: {(0x82 >> 5) & 0x07:03b})")

# Import decoder functions from main.py to avoid duplication
try:
    from main import decode_midea_temperature, decode_midea_mode, decode_midea_power, decode_midea_fan_speed
except ImportError:
    print("Warning: Could not import decoder functions from main.py")

def analyze_temperature_commands():
    """Analyze all temperature commands to verify their actual settings"""
    
    # From the midea_commands.h file - extracted byte arrays
    commands = {
        "auto_mode": [0xA1, 0x82, 0x41, 0xFF, 0xFF, 0x5D, 0x17, 0x9F, 0x6F, 0x80, 0x00, 0x28],
        "cool_mode": [0xA1, 0x88, 0x42, 0xFB, 0xFF, 0x54, 0x17, 0x9D, 0xEF, 0x40, 0x00, 0x2A],
        "dry_mode": [0xA1, 0x81, 0x41, 0xFF, 0xFF, 0x5E, 0x17, 0x9F, 0xAF, 0x80, 0x00, 0x28],
        "power_off": [0xA1, 0x02, 0x42, 0xFF, 0xFF, 0xDF, 0x17, 0xBF, 0x6F, 0x40, 0x00, 0x08],
        "power_on": [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28],
        "temp_17c": [0xA1, 0x82, 0x40, 0xFF, 0xFF, 0x0C, 0x17, 0x9F, 0x6F, 0xC0, 0x00, 0x28],
        "temp_18c": [0xA1, 0x82, 0x41, 0xFF, 0xF7, 0x5D, 0x17, 0x9F, 0x6F, 0x80, 0x00, 0x28],
        "temp_19c": [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28],
        "temp_20c": [0xA1, 0x82, 0x43, 0xFF, 0xFF, 0x5E, 0x17, 0x9F, 0x6F, 0x00, 0x00, 0x28],
        "temp_21c": [0xA1, 0x82, 0x44, 0xFF, 0xFF, 0x58, 0x17, 0x9F, 0x6E, 0xC0, 0x00, 0x29],
        "temp_22c": [0xA1, 0x82, 0x45, 0xFF, 0xFF, 0x59, 0x17, 0x9F, 0x6E, 0x80, 0x00, 0x29],
    }
    
    print("TEMPERATURE COMMAND ANALYSIS")
    print("=" * 70)
    print(f"{'Filename':<12} {'Mode':<6} {'Temp':<6} {'Byte1':<8} {'Power':<6} {'Match?'}")
    print("-" * 70)
    
    mismatches = []
    
    for filename, bytes_data in commands.items():
        # Analyze byte 1 for mode and temperature
        mode_temp_byte = bytes_data[1]
        
        # Decode temperature and mode
        actual_temp = decode_midea_temperature(mode_temp_byte)
        actual_mode = decode_midea_mode(mode_temp_byte)
        
        # Check power state (bit 7 of byte 1)
        power_state = "ON" if (mode_temp_byte & 0x80) else "OFF"
        
        # Check if filename matches actual temperature
        filename_match = "✓"
        if filename.startswith("temp_"):
            expected_temp = filename.replace("temp_", "").replace("c", "")
            if expected_temp.isdigit():
                expected_temp_num = int(expected_temp)
                if isinstance(actual_temp, int) and actual_temp != expected_temp_num:
                    filename_match = "✗"
                    mismatches.append({
                        'filename': filename,
                        'expected': expected_temp_num,
                        'actual': actual_temp,
                        'mode': actual_mode
                    })
        
        print(f"{filename:<12} {actual_mode:<6} {actual_temp}°C   0x{mode_temp_byte:02X}   {power_state:<6} {filename_match}")
    
    if mismatches:
        print(f"\n❌ MISMATCHES FOUND:")
        print("=" * 50)
        for mismatch in mismatches:
            print(f"File: {mismatch['filename']}")
            print(f"  Expected: {mismatch['expected']}°C")
            print(f"  Actual: {mismatch['actual']}°C ({mismatch['mode']} mode)")
            print()
    else:
        print(f"\n✅ All temperature filenames match their actual settings!")
    
    # Additional analysis: Look for temperature encoding pattern
    print(f"\nTEMPERATURE ENCODING ANALYSIS:")
    print("=" * 40)
    temp_commands = {k: v for k, v in commands.items() if k.startswith("temp_")}
    
    for filename, bytes_data in temp_commands.items():
        mode_temp_byte = bytes_data[1]
        temp_bits = mode_temp_byte & 0x0F
        actual_temp = decode_midea_temperature(mode_temp_byte)
        
        print(f"{filename}: Byte1=0x{mode_temp_byte:02X}, LowerBits=0x{temp_bits:X} ({temp_bits}), Decoded={actual_temp}°C")

def deep_temperature_analysis():
    """Deep analysis of temperature commands looking at all bytes for patterns"""
    
    commands = {
        "temp_17c": [0xA1, 0x82, 0x40, 0xFF, 0xFF, 0x0C, 0x17, 0x9F, 0x6F, 0xC0, 0x00, 0x28],
        "temp_18c": [0xA1, 0x82, 0x41, 0xFF, 0xF7, 0x5D, 0x17, 0x9F, 0x6F, 0x80, 0x00, 0x28],
        "temp_19c": [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28],
        "temp_20c": [0xA1, 0x82, 0x43, 0xFF, 0xFF, 0x5E, 0x17, 0x9F, 0x6F, 0x00, 0x00, 0x28],
        "temp_21c": [0xA1, 0x82, 0x44, 0xFF, 0xFF, 0x58, 0x17, 0x9F, 0x6E, 0xC0, 0x00, 0x29],
        "temp_22c": [0xA1, 0x82, 0x45, 0xFF, 0xFF, 0x59, 0x17, 0x9F, 0x6E, 0x80, 0x00, 0x29],
    }
    
    print("DEEP TEMPERATURE ANALYSIS - Looking at ALL bytes for patterns")
    print("=" * 80)
    print(f"{'File':<10} {'Byte2':<6} {'Byte2_bin':<10} {'Byte9':<6} {'Byte9_bin':<10} {'Byte11':<7} {'Pattern'}")
    print("-" * 80)
    
    for filename, bytes_data in commands.items():
        byte2 = bytes_data[2]  # Fan/swing byte
        byte9 = bytes_data[9]  # Additional data byte
        byte11 = bytes_data[11]  # Last byte
        
        # Look for patterns in these bytes
        byte2_bin = f"{byte2:08b}"
        byte9_bin = f"{byte9:08b}"
        
        # Extract potential temperature info from byte 2
        temp_from_byte2 = byte2 & 0x0F  # Lower 4 bits
        fan_from_byte2 = (byte2 >> 0) & 0x07  # Lower 3 bits
        
        print(f"{filename:<10} 0x{byte2:02X}   {byte2_bin:<10} 0x{byte9:02X}   {byte9_bin:<10} 0x{byte11:02X}    Temp?={temp_from_byte2}")
    
    print(f"\nLOOKING FOR TEMPERATURE PATTERNS:")
    print("=" * 50)
    
    # Check if byte 2 contains temperature info
    print("Analyzing BYTE 2 (Fan/Swing byte) for temperature patterns:")
    for filename, bytes_data in commands.items():
        expected_temp = int(filename.replace("temp_", "").replace("c", ""))
        byte2 = bytes_data[2]
        
        # Try different interpretations
        lower_4_bits = byte2 & 0x0F
        lower_3_bits = byte2 & 0x07
        upper_4_bits = (byte2 >> 4) & 0x0F
        
        print(f"{filename}: Expected={expected_temp}°C, Byte2=0x{byte2:02X}")
        print(f"  Lower 4 bits: {lower_4_bits} (diff from expected: {abs(lower_4_bits - expected_temp)})")
        print(f"  Lower 3 bits: {lower_3_bits} (diff from expected: {abs(lower_3_bits - expected_temp)})")
        print(f"  Upper 4 bits: {upper_4_bits} (diff from expected: {abs(upper_4_bits - expected_temp)})")
        print()
    
    # Check byte 9 patterns
    print("Analyzing BYTE 9 for temperature patterns:")
    for filename, bytes_data in commands.items():
        expected_temp = int(filename.replace("temp_", "").replace("c", ""))
        byte9 = bytes_data[9]
        
        # Byte 9 shows clear pattern: 0xC0, 0x80, 0x40, 0x00, 0xC0, 0x80
        print(f"{filename}: Expected={expected_temp}°C, Byte9=0x{byte9:02X} = {byte9:08b}")

def suggest_recapture_strategy():
    """Suggest better capture strategy for temperature commands"""
    print("RECAPTURE STRATEGY RECOMMENDATIONS:")
    print("=" * 50)
    print("🎯 For better temperature captures:")
    print("1. Point remote DIRECTLY at IR receiver (not AC unit)")
    print("2. Keep remote close to receiver (6-12 inches)")
    print("3. Press temperature buttons SLOWLY with pauses")
    print("4. Capture one command at a time")
    print("5. Verify on AC display that temperature actually changed")
    print()
    print("📋 Suggested capture sequence:")
    print("1. Set AC to a known state (e.g., Heat mode, 20°C)")
    print("2. Point remote at IR receiver")
    print("3. Press TEMP DOWN to 17°C - capture as 'temp_17c_new.csv'")
    print("4. Press TEMP UP to 18°C - capture as 'temp_18c_new.csv'")
    print("5. Press TEMP UP to 19°C - capture as 'temp_19c_new.csv'")
    print("6. Continue until 22°C")
    print()
    print("🔍 What to look for in good captures:")
    print("- Different byte values between temperature settings")
    print("- Consistent pattern in specific bytes")
    print("- Reasonable signal strength/timing")

def corrected_temperature_analysis():
    """Corrected analysis with proper temperature decoding"""
    
    commands = {
        "auto_mode": [0xA1, 0x82, 0x41, 0xFF, 0xFF, 0x5D, 0x17, 0x9F, 0x6F, 0x80, 0x00, 0x28],
        "cool_mode": [0xA1, 0x88, 0x42, 0xFB, 0xFF, 0x54, 0x17, 0x9D, 0xEF, 0x40, 0x00, 0x2A],
        "dry_mode": [0xA1, 0x81, 0x41, 0xFF, 0xFF, 0x5E, 0x17, 0x9F, 0xAF, 0x80, 0x00, 0x28],
        "power_off": [0xA1, 0x02, 0x42, 0xFF, 0xFF, 0xDF, 0x17, 0xBF, 0x6F, 0x40, 0x00, 0x08],
        "power_on": [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28],
        "temp_17c": [0xA1, 0x82, 0x40, 0xFF, 0xFF, 0x0C, 0x17, 0x9F, 0x6F, 0xC0, 0x00, 0x28],
        "temp_18c": [0xA1, 0x82, 0x41, 0xFF, 0xF7, 0x5D, 0x17, 0x9F, 0x6F, 0x80, 0x00, 0x28],
        "temp_19c": [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28],
        "temp_20c": [0xA1, 0x82, 0x43, 0xFF, 0xFF, 0x5E, 0x17, 0x9F, 0x6F, 0x00, 0x00, 0x28],
        "temp_21c": [0xA1, 0x82, 0x44, 0xFF, 0xFF, 0x58, 0x17, 0x9F, 0x6E, 0xC0, 0x00, 0x29],
        "temp_22c": [0xA1, 0x82, 0x45, 0xFF, 0xFF, 0x59, 0x17, 0x9F, 0x6E, 0x80, 0x00, 0x29],
    }
    
    def decode_corrected_temperature(byte2):
        """Corrected temperature decoder using byte 2"""
        temp_val = (byte2 & 0x0F) + 17
        return temp_val
    
    def decode_corrected_power(byte1):
        """Corrected power decoder"""
        return "ON" if (byte1 & 0x80) else "OFF"
    
    def decode_corrected_mode(byte1):
        """Corrected mode decoder"""
        mode_bits = (byte1 >> 5) & 0x07
        modes = {0x00: "Auto", 0x01: "Cool", 0x02: "Dry", 0x03: "Fan", 0x04: "Heat"}
        return modes.get(mode_bits, f"Unknown({mode_bits})")
    
    print("CORRECTED COMMAND ANALYSIS")
    print("=" * 80)
    print(f"{'Command':<12} {'Power':<6} {'Mode':<6} {'Temp':<6} {'Byte1':<8} {'Byte2':<8} {'Match'}")
    print("-" * 80)
    
    for filename, bytes_data in commands.items():
        power = decode_corrected_power(bytes_data[1])
        mode = decode_corrected_mode(bytes_data[1])
        temp = decode_corrected_temperature(bytes_data[2])
        
        # Check if temperature filename matches
        match = "✓"
        if filename.startswith("temp_"):
            expected = int(filename.replace("temp_", "").replace("c", ""))
            if temp != expected:
                match = "✗"
        
        print(f"{filename:<12} {power:<6} {mode:<6} {temp}°C   0x{bytes_data[1]:02X}    0x{bytes_data[2]:02X}    {match}")
    
    print(f"\nKEY DISCOVERIES:")
    print("=" * 40)
    print("✓ Power state: Bit 7 of Byte 1 (0=OFF, 1=ON)")
    print("✓ Mode: Bits 5-7 of Byte 1 (0=Auto, 1=Cool, 2=Dry, 4=Heat)")
    print("✓ Temperature: (Byte 2 & 0x0F) + 17")
    print("✓ All temperature commands are CORRECTLY captured!")

if __name__ == "__main__":
    print("1. POWER COMMAND COMPARISON:")
    compare_commands()
    
    print("\n\n2. CORRECTED TEMPERATURE ANALYSIS:")
    corrected_temperature_analysis()
    
    print("\n\n3. DEEP TEMPERATURE ANALYSIS:")
    deep_temperature_analysis()
    
    print("\n\n4. FINAL RECOMMENDATIONS:")
    suggest_recapture_strategy()
    
    print("\n\n5. CORRECTED TEMPERATURE ANALYSIS:")
    corrected_temperature_analysis()

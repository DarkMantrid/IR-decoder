#!/usr/bin/env python3
"""
Regenerate all Midea IR commands with corrected decoder logic
"""

from main import *
import glob
import os

def regenerate_all_commands():
    """Regenerate all commands with suggested names"""
    csv_files = glob.glob("ir_captures/*.csv")
    if not csv_files:
        print("No CSV files found in ir_captures folder")
        return
    
    print(f"Found {len(csv_files)} CSV files to process:")
    for i, file in enumerate(csv_files):
        print(f"  {i+1}. {os.path.basename(file)}")
    
    print("\nProcessing all files with automatic naming...")
    
    for file in csv_files:
        print(f"\n{'='*50}")
        print(f"Processing: {os.path.basename(file)}")
        print('='*50)
        
        # Process the file
        durations = import_from_csv(file)
        if durations is None:
            print(f"Failed to load {file}")
            continue
            
        # Process this file with automatic naming
        process_ir_file_auto(durations, file)

def process_ir_file_auto(durations, filename):
    """Process a single IR file with automatic naming"""
    print(f"Successfully loaded {len(durations)} timing values from {filename}")

    if len(durations) < 4:
        print("Error: Need at least leader pulse, leader space, and one data bit")
        return

    # Find the start of the actual IR signal (skip long idle periods)
    signal_start = find_ir_signal_start(durations)
    if signal_start > 0:
        print(f"Found IR signal starting at position {signal_start} (skipped {signal_start} idle timing values)")
        durations = durations[signal_start:]

    # Validate leader
    leader_pulse = durations[0]
    leader_space = durations[1]

    if not validate_leader(leader_pulse, leader_space):
        print(f"Warning: Leader may be invalid - Pulse: {leader_pulse}us, Space: {leader_space}us")
        print("You may need to adjust the LEADER_PULSE/SPACE thresholds")
    else:
        print(f"Valid Midea leader detected - Pulse: {leader_pulse}us, Space: {leader_space}us")

    # Decode data bits
    bits = []
    for i in range(2, len(durations) - 1, 2):
        if i + 1 < len(durations):
            pulse = durations[i]
            space = durations[i + 1]
            bit = decode_bit(pulse, space)
            bits.append(bit)

    bits_string = ''.join(bits)
    print(f"\nDecoded bits ({len(bits)} total): {bits_string}")

    # Clean up the bits for analysis
    if '?' in bits_string:
        cleaned_bits = clean_bits_string(bits_string)
        print(f"Cleaned bits ({len(cleaned_bits)} total): {cleaned_bits}")
        analysis_bits = cleaned_bits
    else:
        analysis_bits = bits_string

    # Decode Midea command
    if len(analysis_bits) >= 24:  # Need at least some bits for analysis
        print("\n--- Midea AC Command Analysis ---")
        decode_midea_command(analysis_bits)
        
        # Convert bits to bytes for export
        bytes_data = []
        for i in range(0, len(analysis_bits), 8):
            byte_str = analysis_bits[i:i+8]
            if len(byte_str) == 8:
                byte_val = int(byte_str, 2)
                bytes_data.append(byte_val)
        
        # Generate suggested command name automatically
        suggested_name = generate_command_name(bytes_data, filename)
        print(f"\nUsing command name: '{suggested_name}'")
        
        # Export automatically with suggested name
        command_name = suggested_name.replace(' ', '_').replace('-', '_')
        command_name = ''.join(c for c in command_name if c.isalnum() or c == '_')
        
        if command_name:
            export_for_esp_idf(analysis_bits, bytes_data, command_name, durations)
            
            # Create template files on first export
            if not os.path.exists("midea_ir_blaster.h"):
                create_esp_idf_template()
                print("\n✓ Created ESP-IDF template files:")
                print("  - midea_ir_blaster.h (header file)")
                print("  - midea_ir_blaster.c (implementation)")
        else:
            print("Invalid command name generated")
    else:
        print(f"\nWarning: Only {len(analysis_bits)} valid bits found. Need more data for proper decoding.")

if __name__ == "__main__":
    regenerate_all_commands()

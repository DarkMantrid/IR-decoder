#!/usr/bin/env python3
"""
Midea IR Commands Batch Regeneration Tool

This script provides automated batch processing of all IR capture files to
regenerate the complete midea_commands.h header with corrected decoder logic.

PURPOSE:
========
- Batch process all CSV files in the ir_captures/ folder
- Apply consistent naming conventions based on filenames
- Regenerate midea_commands.h with latest decoder improvements
- Provide automated processing without manual intervention

WHEN TO USE:
===========
- After updating the decoder logic in main.py
- When adding new IR capture files to the ir_captures/ folder
- To ensure all commands use the latest decoding algorithms
- Before finalizing the ESP-IDF header file for hardware testing

FEATURES:
=========
- Automatically discovers all .csv files in ir_captures/
- Uses intelligent command naming based on filenames
- Processes files with the latest decoder logic from main.py
- Generates ESP-IDF compatible C arrays and template code
- Shows progress and results for each processed file

USAGE:
======
    python regenerate_commands.py

The script will:
1. Find all CSV files in the ir_captures/ directory
2. Process each file with the current decoder
3. Generate command names based on filenames
4. Export all commands to midea_commands.h
5. Create ESP-IDF template files if they don't exist

REQUIREMENTS:
============
- ir_captures/ folder with CSV files containing IR timing data
- main.py must be in the same directory (imports decoder functions)
- CSV files should follow logic analyzer export format
"""

from main import *
import glob
import os

def regenerate_all_commands():
    """
    Automatically regenerate all IR commands from CSV files.
    
    This function provides fully automated batch processing of IR capture files:
    
    Process:
    1. Scans ir_captures/ folder for all .csv files
    2. Processes each file using the latest decoder logic
    3. Generates command names based on filenames (e.g., "power_on.csv" -> "power_on")
    4. Exports all commands to midea_commands.h with proper C formatting
    5. Creates ESP-IDF template files for hardware implementation
    
    Filename-based naming examples:
    - power_on.csv -> POWER_ON_TIMING[], power_on_bytes[]
    - temp_22c.csv -> TEMP_22C_TIMING[], temp_22c_bytes[]
    - cool_mode.csv -> COOL_MODE_TIMING[], cool_mode_bytes[]
    
    The function automatically handles:
    - Command name sanitization for C identifiers
    - Duplicate detection and handling
    - Error recovery for corrupted files
    - Progress reporting for batch operations
    
    Note: This will overwrite the existing midea_commands.h file.
    """
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

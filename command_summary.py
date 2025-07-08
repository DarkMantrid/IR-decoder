#!/usr/bin/env python3
"""
Midea IR Commands Summary Generator

Copyright (c) 2025 Orpheus Johansson (deadtechsolutions)
Repository: https://github.com/deadtechsolutions/IR-decoder

This script generates a comprehensive summary of all decoded Midea IR commands
that have been exported to the midea_commands.h header file.

PURPOSE:
========
- Lists all available IR commands with their decoded properties
- Shows power state, mode, temperature, fan speed, and swing settings
- Provides usage examples for ESP-IDF integration
- Helps verify that all expected commands were captured and decoded correctly

USAGE:
======
Run after processing IR captures with main.py or regenerate_commands.py:

    python command_summary.py

The script will read midea_commands.h and extract information about all
exported commands, displaying them in an organized table format.

OUTPUT EXAMPLE:
==============
Generated Midea IR Commands Summary
==================================================
Total commands: 12

 1. POWER_ON_TIMING[] & POWER_ON_BYTES[]
    File: power_on.csv
    Power: On, Mode: Heat, Temperature: 22°C
    Fan: Auto, Swing: Off

 2. POWER_OFF_TIMING[] & POWER_OFF_BYTES[]
    File: power_off.csv  
    Power: Off, Mode: Auto, Temperature: 22°C
    Fan: Auto, Swing: Off

[... more commands ...]

REQUIREMENTS:
============
- midea_commands.h file must exist in the current directory
- File should contain properly formatted command exports from main.py
"""

import re

def generate_command_summary():
    """
    Generate a detailed summary report of all decoded IR commands.
    
    This function parses the midea_commands.h file to extract information about
    all exported IR commands, including their decoded properties and usage details.
    
    The summary includes:
    - Total number of commands found
    - Command names and corresponding CSV source files  
    - Decoded AC settings (power, mode, temperature, fan, swing)
    - ESP-IDF usage examples with proper function calls
    
    File Requirements:
        - midea_commands.h must exist in current directory
        - File must contain commands exported by main.py with proper formatting
        
    Output:
        Prints formatted summary to console with:
        - Table of all commands with their properties
        - ESP-IDF code usage examples
        - List of available command identifiers
    """
    try:
        with open('midea_commands.h', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: midea_commands.h not found. Run regenerate_commands.py first.")
        return

    # Extract all command names and their analysis using regex pattern matching
    commands = []
    pattern = r'// Generated Midea AC IR Command: (.+?)\n.*?/\*\n \* Command Analysis:\n \* Power: (.+?)\n \* Mode: (.+?)\n \* Temperature: (.+?)\n \* Fan Speed: (.+?)\n \* Swing: (.+?)\n \*/'
    
    for match in re.finditer(pattern, content, re.DOTALL):
        cmd_name, power, mode, temp, fan, swing = match.groups()
        commands.append((cmd_name, power, mode, temp, fan, swing))

    print('Generated Midea IR Commands Summary')
    print('=' * 50)
    print(f'Generated from CSV files in ir_captures/ folder')
    print(f'Total commands: {len(commands)}')
    print()
    
    # Display detailed information for each command
    for i, (name, power, mode, temp, fan, swing) in enumerate(commands, 1):
        print(f'{i:2d}. {name.upper()}_TIMING[] & {name.upper()}_BYTES[]')
        print(f'    File: {name}.csv')
        print(f'    Power: {power}, Mode: {mode}, Temperature: {temp}')
        print(f'    Fan: {fan}, Swing: {swing}')
        print()

    print('Usage in ESP-IDF:')
    print('-' * 30)
    print('// Send a command using timing array:')
    print('esp_err_t result = send_ir_command(power_on_timing, POWER_ON_TIMING_COUNT);')
    print()
    print('// Or send using byte array:')
    print('esp_err_t result = send_midea_bytes(power_on_bytes, POWER_ON_BYTES_COUNT);')
    print()
    print('Available commands can be used by replacing "power_on" with any of:')
    for name, _, _, _, _, _ in commands:
        print(f'  - {name}')

if __name__ == "__main__":
    generate_command_summary()

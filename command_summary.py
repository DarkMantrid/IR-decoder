#!/usr/bin/env python3
"""
Generate a summary of all Midea IR commands in the header file
"""

import re

def generate_command_summary():
    """Generate a summary report of all commands in the header file"""
    try:
        with open('midea_commands.h', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: midea_commands.h not found. Run regenerate_commands.py first.")
        return

    # Extract all command names and their analysis
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

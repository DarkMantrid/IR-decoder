#!/usr/bin/env python3
"""
Midea AC IR Signal Decoder and ESP-IDF Code Generator

This script decodes infrared signals from Midea air conditioners and generates
ESP-IDF compatible C code for IR transmission. It supports both single file
processing and batch processing of multiple IR captures.

GETTING STARTED:
===============
1. Capture IR signals using a logic analyzer or microcontroller
2. Export timing data as CSV files in the 'ir_captures/' folder
3. Run this script to decode and generate C code

SUPPORTED INPUT FORMATS:
=======================
- Logic analyzer CSV exports (Saleae, PulseView, etc.)
- Text files with timing values (one per line)
- Timing data should be in microseconds (μs)

QUICK USAGE:
===========
Basic usage (processes main CSV file):
    python main.py

Process multiple files interactively:
    python main.py
    # Follow prompts to select files

Programmatic usage:
    from main import process_ir_file, import_from_csv
    durations = import_from_csv('your_file.csv')
    process_ir_file(durations, 'your_file.csv')

OUTPUT:
=======
- midea_commands.h: C arrays for ESP-IDF
- midea_ir_blaster.h/.c: ESP-IDF template code
- Detailed command analysis printed to console

HARDWARE SETUP:
==============
For capturing IR signals:
- IR receiver (e.g., TSOP4838) connected to logic analyzer
- Sample rate: 1MHz+ recommended for accurate timing

For ESP32-C6 IR transmission:
- IR LED connected via current-limiting resistor
- Default GPIO: 18 (configurable in generated code)

The timing data format should be alternating pulse/space durations:
[leader_pulse, leader_space, data_pulse_1, data_space_1, ...]
"""

import csv
import re
import datetime as import_datetime
import os
import glob

# ==============================================================================
# MIDEA AC IR PROTOCOL CONFIGURATION
# ==============================================================================
# These timing parameters define the Midea AC IR protocol characteristics.
# Adjust these thresholds based on your specific IR captures if needed.
# All values are in microseconds (μs).

# Leader sequence (start of transmission)
LEADER_PULSE_MIN = 4000   # Minimum leader pulse duration
LEADER_PULSE_MAX = 5000   # Maximum leader pulse duration  
LEADER_SPACE_MIN = 4000   # Minimum leader space duration
LEADER_SPACE_MAX = 5000   # Maximum leader space duration

# Data bit encoding (pulse width modulation)
SHORT_PULSE_MIN = 400     # Minimum short pulse (represents '0' bit)
SHORT_PULSE_MAX = 700     # Maximum short pulse
SHORT_SPACE_MIN = 400     # Minimum short space
SHORT_SPACE_MAX = 700     # Maximum short space

# Long pulse encoding (represents '1' bit)
LONG_SPACE_MIN = 1550     # Minimum long pulse duration
LONG_SPACE_MAX = 1650     # Maximum long pulse duration

def validate_leader(pulse, space):
    """
    Validate the IR signal leader sequence.
    
    The Midea protocol starts with a specific leader pulse/space pattern
    that identifies it as a valid Midea transmission.
    
    Args:
        pulse (int): Leader pulse duration in microseconds
        space (int): Leader space duration in microseconds
        
    Returns:
        bool: True if leader sequence is valid, False otherwise
        
    Example:
        >>> validate_leader(4424, 4424)
        True
        >>> validate_leader(1000, 1000)  # Too short
        False
    """
    pulse_valid = LEADER_PULSE_MIN <= pulse <= LEADER_PULSE_MAX
    space_valid = LEADER_SPACE_MIN <= space <= LEADER_SPACE_MAX
    return pulse_valid and space_valid

def decode_bit(pulse, space):
    """
    Decode a single data bit from pulse and space durations.
    
    The Midea protocol uses pulse width modulation where:
    - Short pulse (~560μs) = '0' bit
    - Long pulse (~1600μs) = '1' bit
    - Space duration is typically short for both bit types
    
    Args:
        pulse (int): Pulse duration in microseconds
        space (int): Space duration in microseconds
        
    Returns:
        str: '0', '1', or '?' for invalid/unrecognized pulses
        
    Example:
        >>> decode_bit(560, 560)   # Short pulse = 0
        '0'
        >>> decode_bit(1600, 560)  # Long pulse = 1
        '1'
    """
    # Check space duration (should be short for both 0 and 1)
    if not (SHORT_SPACE_MIN <= space <= SHORT_SPACE_MAX):
        # Allow slightly longer spaces for end of transmission
        if space > 700:
            return '?'
    
    # Check pulse duration to determine bit value
    if SHORT_PULSE_MIN <= pulse <= SHORT_PULSE_MAX:
        return '0'  # Short pulse = 0
    elif LONG_SPACE_MIN <= pulse <= LONG_SPACE_MAX:
        return '1'  # Long pulse = 1
    else:
        return '?'  # Invalid pulse duration

def decode_midea_temperature(byte_val):
    """
    Decode temperature setting from Midea command byte.
    
    Temperature is encoded in the lower 4 bits of Byte 2 using the formula:
    temperature = (byte2 & 0x0F) + 17
    
    This gives a temperature range of 17°C to 32°C (16 possible values).
    
    Args:
        byte_val (int): Byte 2 from the Midea command (8-bit value)
        
    Returns:
        int or str: Temperature in Celsius, or "Unknown" string for invalid values
        
    Example:
        >>> decode_midea_temperature(0x05)  # 0x05 + 17 = 22°C
        22
        >>> decode_midea_temperature(0x00)  # 0x00 + 17 = 17°C  
        17
    """
    # Based on analysis: temperature is in Byte 2, formula: (byte2 & 0x0F) + 17
    temp_bits = byte_val & 0x0F
    temperature = temp_bits + 17
    
    # Validate reasonable temperature range
    if 16 <= temperature <= 30:
        return temperature
    else:
        return f"Unknown ({temp_bits})"

def decode_midea_mode(byte_val):
    """
    Decode AC operation mode from Midea command byte.
    
    The mode is encoded in bits 5-7 (upper 3 bits) of Byte 1.
    
    Args:
        byte_val (int): Byte 1 from the Midea command
        
    Returns:
        str: Human-readable mode name
        
    Mode mapping:
        000 (0): Auto
        001 (1): Cool  
        010 (2): Dry
        011 (3): Fan only
        100 (4): Heat
        
    Example:
        >>> decode_midea_mode(0x82)  # bits 5-7 = 100 = Heat mode
        'Heat'
        >>> decode_midea_mode(0x22)  # bits 5-7 = 001 = Cool mode  
        'Cool'
    """
    mode_bits = (byte_val >> 5) & 0x07  # Extract bits 5-7
    modes = {
        0x00: "Auto",
        0x01: "Cool", 
        0x02: "Dry",
        0x03: "Fan",
        0x04: "Heat"
    }
    return modes.get(mode_bits, f"Unknown mode ({mode_bits})")

def decode_midea_fan_speed(byte_val):
    """
    Decode fan speed setting from Midea command byte.
    
    Fan speed is encoded in the lower 3 bits (bits 0-2) of Byte 3.
    
    Args:
        byte_val (int): Byte 3 from the Midea command
        
    Returns:
        str: Human-readable fan speed description
        
    Fan speed mapping:
        000 (0): Auto
        001 (1): Low
        010 (2): Medium  
        011 (3): High
        111 (7): Silent
        
    Example:
        >>> decode_midea_fan_speed(0x01)  # bits 0-2 = 001 = Low
        'Low'
        >>> decode_midea_fan_speed(0x07)  # bits 0-2 = 111 = Silent
        'Silent'
    """
    fan_bits = byte_val & 0x07  # Extract lower 3 bits
    speeds = {
        0x00: "Auto",
        0x01: "Low",
        0x02: "Medium", 
        0x03: "High",
        0x07: "Silent"
    }
    return speeds.get(fan_bits, f"Unknown speed ({fan_bits})")

def decode_midea_swing(byte_val):
    """
    Decode swing (oscillation) settings from Midea command byte.
    
    Swing settings are encoded in bits 4-5 of Byte 3:
    - Bit 4: Vertical swing (up/down oscillation)
    - Bit 5: Horizontal swing (left/right oscillation)
    
    Args:
        byte_val (int): Byte 3 from the Midea command
        
    Returns:
        str: Human-readable swing status ("Off", "Vertical", "Horizontal", or "Vertical + Horizontal")
        
    Example:
        >>> decode_midea_swing(0x10)  # bit 4 = 1 = Vertical swing
        'Vertical'
        >>> decode_midea_swing(0x30)  # bits 4+5 = 1 = Both directions
        'Vertical + Horizontal'
        >>> decode_midea_swing(0x00)  # bits 4+5 = 0 = No swing
        'Off'
    """
    swing_vertical = (byte_val >> 4) & 0x01
    swing_horizontal = (byte_val >> 5) & 0x01
    
    swing_status = []
    if swing_vertical:
        swing_status.append("Vertical")
    if swing_horizontal:
        swing_status.append("Horizontal")
    
    return " + ".join(swing_status) if swing_status else "Off"

def decode_midea_power(byte_val):
    """
    Decode power state from Midea command byte.
    
    The power state is encoded in bit 7 (MSB) of Byte 1.
    
    Args:
        byte_val (int): Byte 1 from the Midea command
        
    Returns:
        str: "On" if bit 7 is set, "Off" if bit 7 is clear
        
    Example:
        >>> decode_midea_power(0x82)  # bit 7 = 1 = On
        'On'
        >>> decode_midea_power(0x02)  # bit 7 = 0 = Off
        'Off'
    """
    power_bit = (byte_val >> 7) & 0x01  # Use bit 7 instead of bit 5
    return "On" if power_bit else "Off"

def decode_midea_command(bits_str):
    """
    Decode a complete Midea AC command from binary bit string.
    
    This function performs comprehensive analysis of a Midea IR command,
    extracting and displaying all relevant AC settings and validating
    the command structure.
    
    Args:
        bits_str (str): Binary string representing the decoded IR signal
                       (e.g., "101010011001..." - typically 48+ bits)
    
    Process:
        1. Converts binary string to byte array
        2. Analyzes each byte for specific AC functions
        3. Calculates and validates checksum
        4. Displays detailed breakdown of all settings
        
    Expected Command Structure (6+ bytes):
        Byte 0: Command identifier (usually 0xA1)
        Byte 1: Power state (bit 7) + Mode (bits 5-7)
        Byte 2: Temperature setting (bits 0-3)
        Byte 3: Fan speed (bits 0-2) + Swing (bits 4-5)
        Byte 4: Additional settings
        Byte 5: Checksum (XOR of all previous bytes)
        
    Example:
        >>> decode_midea_command("10100001100000100100001011111111...")
        Raw bytes: A1 82 42 FF FF 5F
        
        --- Detailed Command Analysis ---
        Byte 0 (Command): 0xA1
        Byte 1 (Power/Mode): 0x82 - Power: On, Mode: Heat
        Byte 2 (Temperature): 0x42 - Temperature: 22°C
        ...
    """
    if len(bits_str) < 48:
        print(f"Warning: Expected 48 bits, got {len(bits_str)} bits")
        # Pad with zeros if too short
        bits_str = bits_str.ljust(48, '0')
    
    # Convert binary string to bytes
    bytes_data = []
    for i in range(0, len(bits_str), 8):
        byte_str = bits_str[i:i+8]
        if len(byte_str) == 8:
            byte_val = int(byte_str, 2)
            bytes_data.append(byte_val)
    
    print(f"Raw bytes: {' '.join(f'{b:02X}' for b in bytes_data)}")
    
    if len(bytes_data) >= 6:
        # Enhanced Midea AC command structure analysis (corrected mapping)
        print(f"\n--- Detailed Command Analysis ---")
        print(f"Byte 0 (Command): 0x{bytes_data[0]:02X}")
        print(f"Byte 1 (Power/Mode): 0x{bytes_data[1]:02X} - Power: {decode_midea_power(bytes_data[1])}, Mode: {decode_midea_mode(bytes_data[1])}")
        print(f"Byte 2 (Temperature): 0x{bytes_data[2]:02X} - Temperature: {decode_midea_temperature(bytes_data[2])}°C")
        print(f"Byte 3 (Fan/Swing): 0x{bytes_data[3]:02X} - Fan: {decode_midea_fan_speed(bytes_data[3])}, Swing: {decode_midea_swing(bytes_data[3])}")
        print(f"Byte 4 (Extra): 0x{bytes_data[4]:02X}")
        print(f"Byte 5 (Checksum): 0x{bytes_data[5]:02X}")
        
        # Calculate checksum (XOR of all bytes except last)
        calculated_checksum = 0
        for i in range(len(bytes_data) - 1):
            calculated_checksum ^= bytes_data[i]
        
        if len(bytes_data) > 5:
            checksum_valid = calculated_checksum == bytes_data[-1]
            print(f"Checksum: {'✓ Valid' if checksum_valid else '✗ Invalid'} (calculated: 0x{calculated_checksum:02X})")
            
        # Show bit-level analysis for debugging
        print(f"\n--- Bit Analysis ---")
        for i, byte_val in enumerate(bytes_data[:6]):
            print(f"Byte {i}: 0x{byte_val:02X} = {byte_val:08b}")
            
    if len(bytes_data) < 6:
        print("Warning: Incomplete command - need at least 6 bytes for proper Midea decoding")

def import_from_csv(filename):
    """
    Import IR timing data from logic analyzer CSV export files.
    
    Supports various CSV formats from popular logic analyzers including:
    - Saleae Logic (Time [s], Channel columns)
    - PulseView (Time, Digital channels)
    - Generic time-based CSV formats
    
    The function automatically detects the CSV format and extracts timing
    transitions, calculating pulse/space durations in microseconds.
    
    Args:
        filename (str): Path to the CSV file containing IR capture data
        
    Returns:
        list or None: List of pulse/space durations in microseconds,
                     or None if file cannot be read or format not recognized
                     
    CSV Format Requirements:
        - Must have a time column (seconds, milliseconds, or microseconds)
        - Must have at least one digital channel showing IR signal transitions
        - Time values should be in ascending order
        
    Example:
        >>> durations = import_from_csv('ir_captures/power_on.csv')
        >>> print(f"Loaded {len(durations)} timing values")
        Loaded 96 timing values
    """
    durations = []
    
    try:
        with open(filename, 'r') as file:
            # Try to detect CSV format automatically
            sample = file.read(1024)
            file.seek(0)
            
            # Check for common logic analyzer CSV formats
            if 'Time [s]' in sample or 'Time(s)' in sample:
                durations = parse_saleae_csv(file)
            elif 'Time' in sample and 'Channel' in sample:
                durations = parse_generic_csv(file)
            else:
                print("Unknown CSV format. Please check the file format.")
                return None
                
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None
    
    return durations

def parse_saleae_csv(file):
    """Parse Saleae Logic CSV export format"""
    durations = []
    reader = csv.DictReader(file)
    
    prev_time = None
    prev_state = None
    
    for row in reader:
        try:
            # Get time in seconds and convert to microseconds
            time_s = float(row.get('Time [s]', row.get('Time(s)', 0)))
            time_us = time_s * 1_000_000
            
            # Get digital state - look for any channel column
            state_key = None
            for key in row.keys():
                if 'Channel' in key or 'Digital' in key or key.strip().startswith('Channel'):
                    state_key = key
                    break
            
            if state_key:
                state = int(row[state_key])
            else:
                # If no channel found, try to get the second column
                keys = list(row.keys())
                if len(keys) > 1:
                    state = int(row[keys[1]])
                else:
                    continue
                
            if prev_time is not None and prev_state is not None:
                duration = int(time_us - prev_time)
                if duration > 0:  # Filter out zero-duration events
                    durations.append(duration)
            
            prev_time = time_us
            prev_state = state
            
        except (ValueError, KeyError) as e:
            continue
    
    return durations

def parse_generic_csv(file):
    """Parse generic logic analyzer CSV format"""
    durations = []
    reader = csv.DictReader(file)
    
    prev_time = None
    
    for row in reader:
        try:
            # Try different time column names
            time_val = None
            for time_key in ['Time', 'Time [s]', 'Time(s)', 'Timestamp']:
                if time_key in row:
                    time_val = float(row[time_key])
                    break
            
            if time_val is None:
                continue
                
            # Convert to microseconds if needed
            if time_val < 1:  # Assume seconds
                time_us = time_val * 1_000_000
            elif time_val < 1000:  # Assume milliseconds
                time_us = time_val * 1000
            else:  # Assume already microseconds
                time_us = time_val
            
            if prev_time is not None:
                duration = int(time_us - prev_time)
                if duration > 0:
                    durations.append(duration)
            
            prev_time = time_us
            
        except (ValueError, KeyError):
            continue
    
    return durations

def import_from_text(filename):
    """Import timing data from simple text file (one duration per line)"""
    durations = []
    
    try:
        with open(filename, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    try:
                        # Extract number from line (handles various formats)
                        numbers = re.findall(r'[\d.]+', line)
                        if numbers:
                            duration = float(numbers[0])
                            # Convert to microseconds if needed
                            if duration < 1:  # Assume seconds
                                duration *= 1_000_000
                            elif duration < 1000:  # Assume milliseconds
                                duration *= 1000
                            durations.append(int(duration))
                    except ValueError:
                        continue
                        
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    except Exception as e:
        print(f"Error reading text file: {e}")
        return None
    
    return durations

def find_ir_signal_start(durations, min_pulse_length=4000):
    """Find the start of the actual IR signal, skipping long idle periods"""
    for i in range(0, len(durations) - 1, 2):
        if i + 1 < len(durations):
            pulse = durations[i]
            space = durations[i + 1]
            # Look for the first reasonable pulse (not the long idle period)
            if pulse >= min_pulse_length and space >= min_pulse_length:
                return i
    return 0

def clean_bits_string(bits_str):
    """Clean up the bits string by removing invalid bits and finding the main signal"""
    # Remove leading and trailing invalid bits
    start = 0
    end = len(bits_str)
    
    # Find first valid bit
    for i, bit in enumerate(bits_str):
        if bit in '01':
            start = i
            break
    
    # Find last valid bit
    for i in range(len(bits_str) - 1, -1, -1):
        if bits_str[i] in '01':
            end = i + 1
            break
    
    cleaned = bits_str[start:end]
    
    # Replace any remaining '?' with '0' (conservative approach)
    cleaned = cleaned.replace('?', '0')
    
    return cleaned

def export_for_esp_idf(bits_string, bytes_data, command_name, durations, filename="midea_commands.h"):
    """Export decoded command for ESP-IDF C code"""
    
    # Generate timing data array
    timing_data = []
    for i in range(2, len(durations) - 1, 2):
        if i + 1 < len(durations):
            pulse = durations[i]
            space = durations[i + 1]
            timing_data.extend([pulse, space])
    
    # Create C header content
    header_content = f"""
// Generated Midea AC IR Command: {command_name}
// Decoded on {import_datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// Raw bytes: {' '.join(f'0x{b:02X}' for b in bytes_data)}

#define {command_name.upper()}_TIMING_COUNT {len(timing_data)}
static const uint32_t {command_name.lower()}_timing[] = {{
"""
    
    # Add timing data in groups of 8 for readability
    for i in range(0, len(timing_data), 8):
        line_data = timing_data[i:i+8]
        line = "    " + ", ".join(f"{t:4d}" for t in line_data)
        if i + 8 < len(timing_data):
            line += ","
        header_content += line + "\n"
    
    header_content += "};\n\n"
    
    # Add raw bytes array
    header_content += f"#define {command_name.upper()}_BYTES_COUNT {len(bytes_data)}\n"
    header_content += f"static const uint8_t {command_name.lower()}_bytes[] = {{\n"
    header_content += "    " + ", ".join(f"0x{b:02X}" for b in bytes_data) + "\n"
    header_content += "};\n\n"
    
    # Add command info as comments
    if len(bytes_data) >= 6:
        header_content += f"/*\n"
        header_content += f" * Command Analysis:\n"
        header_content += f" * Power: {decode_midea_power(bytes_data[1])}\n"
        header_content += f" * Mode: {decode_midea_mode(bytes_data[1])}\n" 
        header_content += f" * Temperature: {decode_midea_temperature(bytes_data[2])}°C\n"
        header_content += f" * Fan Speed: {decode_midea_fan_speed(bytes_data[3])}\n"
        header_content += f" * Swing: {decode_midea_swing(bytes_data[3])}\n"
        header_content += f" */\n\n"
    
    # Write to file
    try:
        with open(filename, 'a') as f:
            f.write(header_content)
        print(f"\n✓ Exported command '{command_name}' to {filename}")
        print(f"  - Timing array: {command_name.lower()}_timing[{len(timing_data)}]")
        print(f"  - Bytes array: {command_name.lower()}_bytes[{len(bytes_data)}]")
    except Exception as e:
        print(f"Error writing to {filename}: {e}")

def create_esp_idf_template():
    """Create a template ESP-IDF IR blaster code"""
    template = """/*
 * Midea AC IR Blaster for ESP32-C6
 * Generated by Midea IR Decoder
 * 
 * Hardware setup:
 * - IR LED connected to GPIO pin (e.g., GPIO 18)
 * - Use appropriate current limiting resistor
 * 
 * Usage:
 * 1. Include this header in your main.c
 * 2. Call send_ir_command() with desired command timing array
 */

#ifndef MIDEA_IR_COMMANDS_H
#define MIDEA_IR_COMMANDS_H

#include <stdint.h>
#include "driver/rmt_tx.h"
#include "driver/gpio.h"

// IR Protocol Configuration
#define IR_CARRIER_FREQ_HZ    38000    // 38kHz carrier frequency
#define IR_GPIO_NUM           GPIO_NUM_18  // Change to your IR LED pin
#define IR_RESOLUTION_HZ      1000000  // 1MHz resolution for microsecond timing

// Midea AC Protocol timing (microseconds)
#define MIDEA_LEADER_PULSE    4424
#define MIDEA_LEADER_SPACE    4424
#define MIDEA_SHORT_PULSE     560
#define MIDEA_SHORT_SPACE     560
#define MIDEA_LONG_PULSE      1600    // For '1' bits
#define MIDEA_REPEAT_SPACE    5000    // Space before repeat

// Function declarations
esp_err_t ir_blaster_init(void);
esp_err_t send_ir_command(const uint32_t* timing_data, size_t count);
esp_err_t send_midea_bytes(const uint8_t* bytes, size_t count);

#endif // MIDEA_IR_COMMANDS_H
"""
    
    with open("midea_ir_blaster.h", 'w') as f:
        f.write(template)
    
    # Create implementation file
    impl = """/*
 * Midea AC IR Blaster Implementation
 * ESP32-C6 RMT Driver Implementation
 */

#include "midea_ir_blaster.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include <stdlib.h>

static const char* TAG = "IR_BLASTER";
static rmt_channel_handle_t ir_channel = NULL;
static rmt_encoder_handle_t ir_encoder = NULL;

esp_err_t ir_blaster_init(void) {
    // Configure RMT TX channel
    rmt_tx_channel_config_t tx_config = {
        .gpio_num = IR_GPIO_NUM,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = IR_RESOLUTION_HZ,
        .mem_block_symbols = 64,
        .trans_queue_depth = 4,
    };
    
    ESP_ERROR_CHECK(rmt_new_tx_channel(&tx_config, &ir_channel));
    
    // Configure IR carrier
    rmt_carrier_config_t carrier_config = {
        .frequency_hz = IR_CARRIER_FREQ_HZ,
        .duty_cycle = 0.33,  // 33% duty cycle
    };
    
    ESP_ERROR_CHECK(rmt_apply_carrier(ir_channel, &carrier_config));
    ESP_ERROR_CHECK(rmt_enable(ir_channel));
    
    ESP_LOGI(TAG, "IR Blaster initialized on GPIO %d", IR_GPIO_NUM);
    return ESP_OK;
}

esp_err_t send_ir_command(const uint32_t* timing_data, size_t count) {
    if (!ir_channel || !timing_data || count == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    // Convert timing to RMT symbols
    rmt_symbol_word_t* symbols = malloc((count/2 + 1) * sizeof(rmt_symbol_word_t));
    if (!symbols) {
        return ESP_ERR_NO_MEM;
    }
    
    // First symbol is leader pulse + space
    symbols[0].level0 = 1;
    symbols[0].duration0 = MIDEA_LEADER_PULSE;
    symbols[0].level1 = 0;
    symbols[0].duration1 = MIDEA_LEADER_SPACE;
    
    // Convert timing pairs to RMT symbols
    for (size_t i = 0; i < count - 1; i += 2) {
        symbols[i/2 + 1].level0 = 1;  // Pulse (high)
        symbols[i/2 + 1].duration0 = timing_data[i];
        symbols[i/2 + 1].level1 = 0;  // Space (low)
        symbols[i/2 + 1].duration1 = timing_data[i + 1];
    }
    
    // Transmit
    rmt_transmit_config_t tx_config = {
        .loop_count = 0,  // No repeat
    };
    
    esp_err_t ret = rmt_transmit(ir_channel, ir_encoder, symbols, count/2 + 1, &tx_config);
    
    free(symbols);
    return ret;
}

esp_err_t send_midea_bytes(const uint8_t* bytes, size_t count) {
    // Convert bytes to timing array (implement based on your protocol)
    // This is a simplified version - you may need to adjust
    
    size_t timing_count = count * 8 * 2;  // 8 bits per byte, 2 timings per bit
    uint32_t* timing_data = malloc(timing_count * sizeof(uint32_t));
    
    if (!timing_data) {
        return ESP_ERR_NO_MEM;
    }
    
    size_t timing_idx = 0;
    
    for (size_t byte_idx = 0; byte_idx < count; byte_idx++) {
        uint8_t byte = bytes[byte_idx];
        
        for (int bit = 7; bit >= 0; bit--) {
            // Pulse is always short
            timing_data[timing_idx++] = MIDEA_SHORT_PULSE;
            
            // Space determines bit value
            if (byte & (1 << bit)) {
                timing_data[timing_idx++] = MIDEA_LONG_PULSE;  // '1' bit
            } else {
                timing_data[timing_idx++] = MIDEA_SHORT_SPACE; // '0' bit
            }
        }
    }
    
    esp_err_t ret = send_ir_command(timing_data, timing_count);
    free(timing_data);
    return ret;
}
"""
    
    with open("midea_ir_blaster.c", 'w') as f:
        f.write(impl)

def process_multiple_files():
    """Process multiple CSV files in the ir_captures folder"""
    csv_files = glob.glob("ir_captures/*.csv")
    if not csv_files:
        print("No CSV files found in ir_captures folder")
        return
    
    print(f"Found {len(csv_files)} CSV files:")
    for i, file in enumerate(csv_files):
        print(f"  {i+1}. {os.path.basename(file)}")
    
    choice = input("\nProcess all files? (y/n) or enter file number: ").strip().lower()
    
    if choice == 'y':
        files_to_process = csv_files
    elif choice.isdigit() and 1 <= int(choice) <= len(csv_files):
        files_to_process = [csv_files[int(choice)-1]]
    else:
        print("Invalid choice")
        return
    
    for file in files_to_process:
        print(f"\n{'='*50}")
        print(f"Processing: {os.path.basename(file)}")
        print('='*50)
        
        # Process the file (similar to main logic)
        durations = import_from_csv(file)
        if durations is None:
            print(f"Failed to load {file}")
            continue
            
        # Process this file with the main logic
        process_ir_file(durations, file)

def process_ir_file(durations, filename):
    """Process a single IR file"""
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
        
        # Generate suggested command name based on decoded data and filename
        suggested_name = generate_command_name(bytes_data, filename)
        print(f"\nSuggested command name: '{suggested_name}'")
        
        # Ask user for command name with suggestion
        user_input = input(f"Enter command name (press Enter for '{suggested_name}'): ").strip()
        command_name = user_input if user_input else suggested_name
        
        if command_name:
            # Clean command name for C identifier
            command_name = command_name.replace(' ', '_').replace('-', '_')
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
                print("Invalid command name")
        else:
            print("Skipping export")
    else:
        print(f"\nWarning: Only {len(analysis_bits)} valid bits found. Need more data for proper decoding.")

def generate_command_name(bytes_data, filename):
    """Generate a suggested command name based on filename (primary) and decoded data (validation)"""
    # Extract base filename without path and extension
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # Use filename as the primary source for command naming
    suggested = base_name.lower()
    
    # Clean up the name for C identifier
    suggested = suggested.replace('-', '_').replace(' ', '_')
    suggested = ''.join(c for c in suggested if c.isalnum() or c == '_')
    
    # Optional: Add validation comment showing if filename matches decoded data
    if len(bytes_data) >= 6:
        power = decode_midea_power(bytes_data[1])
        mode = decode_midea_mode(bytes_data[1])
        temp = decode_midea_temperature(bytes_data[2])
        
        # Add decoded info as suffix only if filename doesn't contain enough info
        filename_lower = base_name.lower()
        has_temp = any(str(i) in filename_lower for i in range(16, 31))
        has_mode = any(mode_word in filename_lower for mode_word in ['auto', 'cool', 'heat', 'dry', 'fan'])
        has_power = any(power_word in filename_lower for power_word in ['power', 'on', 'off'])
        
        # If filename is too generic, add decoded info
        if not (has_temp or has_mode or has_power):
            suggested += f"_{power.lower()}"
            if mode != "Auto" and mode != "Unknown mode (0)":
                suggested += f"_{mode.lower()}"
            if isinstance(temp, int) and 16 <= temp <= 30:
                suggested += f"_{temp}c"
    
    return suggested

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
"""
Main script execution for processing Midea IR signals.

SCRIPT BEHAVIOR:
===============
When run directly, this script will:

1. Attempt to load the default file 'ir_captures/digital.csv'
2. Process the IR timing data to decode the Midea command
3. Display detailed analysis of the decoded AC settings
4. Export the command as C arrays for ESP-IDF
5. Optionally process additional CSV files in batch mode

ALTERNATIVE USAGE PATTERNS:
==========================

Process a specific file:
    durations = import_from_csv('ir_captures/your_file.csv')
    process_ir_file(durations, 'ir_captures/your_file.csv')

Process all files at once:
    process_multiple_files()

Import from text file instead of CSV:
    durations = import_from_text('your_file.txt')
    process_ir_file(durations, 'your_file.txt')

EXPECTED OUTPUT FILES:
=====================
- midea_commands.h: C header with all decoded commands
- midea_ir_blaster.h: ESP-IDF template header
- midea_ir_blaster.c: ESP-IDF template implementation

TROUBLESHOOTING:
===============
- Ensure CSV files are properly formatted with time and channel columns
- Check that timing values are in microseconds
- Verify IR signal has proper Midea leader sequence (~4424μs pulse/space)
- Adjust protocol timing parameters if needed for your specific AC model
"""
if __name__ == "__main__":
    # Load captured IR data from the ir_captures folder
    durations = import_from_csv('ir_captures/digital.csv')
    if durations is None:
        print("Failed to import data from ir_captures/digital.csv")
        print("You can also process multiple files or use:")
        print("- process_multiple_files() to choose from available CSV files")
        print("- durations = import_from_text('your_file.txt') for text files")
        exit(1)
    
    # Process the main file
    process_ir_file(durations, 'ir_captures/digital.csv')
    
    # Optionally process multiple files
    print("\n" + "="*50)
    process_more = input("Process more CSV files? (y/n): ").strip().lower()
    if process_more == 'y':
        process_multiple_files()

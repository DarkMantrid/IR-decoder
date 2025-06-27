# Midea AC IR Signal Decoder
# 
# Instructions for use:
# 1. Capture IR signal using an IR receiver and microcontroller
# 2. Record timing durations in microseconds (μs)
# 3. Replace the 'durations' list below with your captured data
# 4. Run this script to decode the Midea AC command
#
# The durations list should contain alternating pulse/space timings:
# [leader_pulse, leader_space, data_pulse_1, data_space_1, data_pulse_2, data_space_2, ...]
#
# Replace this with your actual durations (in microseconds)
# Alternate high/low durations: [leader_pulse, leader_space, pulse, space, ...]
durations = [
    4424, 4424,  # Leader pulse and space for Midea (adjust based on your capture)
    560, 1690,   # Bit 1 (short pulse, long space) -> '1'
    560, 560,    # Bit 2 (short pulse, short space) -> '0'
    # ... add the rest of your timings here
    # Midea typically sends 48 bits total
]

# Midea AC IR Protocol Parameters
# Adjust these thresholds based on your specific captures
LEADER_PULSE_MIN = 4000   # us
LEADER_PULSE_MAX = 5000   # us
LEADER_SPACE_MIN = 4000   # us
LEADER_SPACE_MAX = 5000   # us

SHORT_PULSE_MIN = 400     # us
SHORT_PULSE_MAX = 700     # us
SHORT_SPACE_MIN = 400     # us
SHORT_SPACE_MAX = 700     # us

LONG_SPACE_MIN = 1550     # us - adjusted for your signal  
LONG_SPACE_MAX = 1650     # us - adjusted for your signal

# Duplicate definition of validate_leader removed to avoid redefinition error.

def decode_bit(pulse, space):
    """Decode a single bit based on pulse and space durations"""
    # For this Midea protocol, it appears to use pulse width modulation:
    # Short pulse = 0, Long pulse = 1
    
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

def decode_midea_command(bits_str):
    """Decode Midea AC command from bit string"""
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
        # Enhanced Midea AC command structure analysis
        print(f"\n--- Detailed Command Analysis ---")
        print(f"Byte 0 (Command): 0x{bytes_data[0]:02X} - Power: {decode_midea_power(bytes_data[0])}")
        print(f"Byte 1 (Mode/Temp): 0x{bytes_data[1]:02X} - Mode: {decode_midea_mode(bytes_data[1])}, Temp: {decode_midea_temperature(bytes_data[1])}°C")
        print(f"Byte 2 (Fan/Swing): 0x{bytes_data[2]:02X} - Fan: {decode_midea_fan_speed(bytes_data[2])}, Swing: {decode_midea_swing(bytes_data[2])}")
        print(f"Byte 3 (Extra): 0x{bytes_data[3]:02X}")
        print(f"Byte 4 (Timer/Extra): 0x{bytes_data[4]:02X}")
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

def decode_midea_temperature(byte_val):
    """Decode temperature from Midea command byte"""
    # Midea temperature encoding varies by model, common patterns:
    temp_mappings = {
        0x00: 16, 0x01: 17, 0x02: 18, 0x03: 19, 0x04: 20,
        0x05: 21, 0x06: 22, 0x07: 23, 0x08: 24, 0x09: 25,
        0x0A: 26, 0x0B: 27, 0x0C: 28, 0x0D: 29, 0x0E: 30
    }
    
    # Extract temperature bits (usually lower 4 bits)
    temp_bits = byte_val & 0x0F
    return temp_mappings.get(temp_bits, f"Unknown ({temp_bits})")

def decode_midea_mode(byte_val):
    """Decode AC mode from Midea command byte"""
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
    """Decode fan speed from Midea command byte"""
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
    """Decode swing settings from Midea command byte"""
    swing_vertical = (byte_val >> 4) & 0x01
    swing_horizontal = (byte_val >> 5) & 0x01
    
    swing_status = []
    if swing_vertical:
        swing_status.append("Vertical")
    if swing_horizontal:
        swing_status.append("Horizontal")
    
    return " + ".join(swing_status) if swing_status else "Off"

def decode_midea_power(byte_val):
    """Decode power state from Midea command byte"""
    power_bit = (byte_val >> 5) & 0x01
    return "On" if power_bit else "Off"

import csv
import re

def import_from_csv(filename):
    """Import timing data from logic analyzer CSV export"""
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

def print_import_instructions():
    """Print instructions for importing data from logic analyzers"""
    print("""
=== Logic Analyzer Import Instructions ===

1. SALEAE LOGIC:
   - Capture your IR signal on any digital channel
   - Go to Data > Export Data > Export Timing/State
   - Choose CSV format
   - Save and use: durations = import_from_csv('your_file.csv')

2. SIGROK/PULSEVIEW:
   - Capture IR signal
   - File > Export > CSV
   - Use: durations = import_from_csv('your_file.csv')

3. DSLogic/DreamSourceLab:
   - Export as CSV with timing data
   - Use: durations = import_from_csv('your_file.csv')

4. GENERIC TEXT FILE:
   - Create a text file with one timing value per line (in microseconds)
   - Use: durations = import_from_text('your_file.txt')

Example usage:
# Replace the manual durations list with:
# durations = import_from_csv('ir_capture.csv')
# if durations is None:
#     print("Failed to import data, using example data")
#     durations = [4424, 4424, 560, 1690, 560, 560]  # fallback

""")

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

def export_for_esp_idf(bits_string, bytes_data, command_name, filename="midea_commands.h"):
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
        header_content += f" * Power: {decode_midea_power(bytes_data[0])}\n"
        header_content += f" * Mode: {decode_midea_mode(bytes_data[1])}\n" 
        header_content += f" * Temperature: {decode_midea_temperature(bytes_data[1])}°C\n"
        header_content += f" * Fan Speed: {decode_midea_fan_speed(bytes_data[2])}\n"
        header_content += f" * Swing: {decode_midea_swing(bytes_data[2])}\n"
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
    rmt_symbol_word_t* symbols = malloc(count * sizeof(rmt_symbol_word_t));
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

import datetime as import_datetime

# Midea AC IR Signal Decoder
# 
# Instructions for use:
# 1. Capture IR signal using an IR receiver and microcontroller
# 2. Record timing durations in microseconds (μs)
# 3. Replace the 'durations' list below with your captured data
# 4. Run this script to decode the Midea AC command
#
# The durations list should contain alternating pulse/space timings:
# [leader_pulse, leader_space, data_pulse_1, data_space_1, data_pulse_2, data_space_2, ...]
#
# Replace this with your actual durations (in microseconds)
# Alternate high/low durations: [leader_pulse, leader_space, pulse, space, ...]
durations = [
    4424, 4424,  # Leader pulse and space for Midea (adjust based on your capture)
    560, 1690,   # Bit 1 (short pulse, long space) -> '1'
    560, 560,    # Bit 2 (short pulse, short space) -> '0'
    # ... add the rest of your timings here
    # Midea typically sends 48 bits total
]

# Midea AC IR Protocol Parameters
# Adjust these thresholds based on your specific captures
LEADER_PULSE_MIN = 4000   # us
LEADER_PULSE_MAX = 5000   # us
LEADER_SPACE_MIN = 4000   # us
LEADER_SPACE_MAX = 5000   # us

SHORT_PULSE_MIN = 400     # us
SHORT_PULSE_MAX = 700     # us
SHORT_SPACE_MIN = 400     # us
SHORT_SPACE_MAX = 700     # us

LONG_SPACE_MIN = 1550     # us - adjusted for your signal  
LONG_SPACE_MAX = 1650     # us - adjusted for your signal

def validate_leader(pulse, space):
    """Check if the first pulse/space pair is a valid Midea leader"""
    pulse_valid = LEADER_PULSE_MIN <= pulse <= LEADER_PULSE_MAX
    space_valid = LEADER_SPACE_MIN <= space <= LEADER_SPACE_MAX
    return pulse_valid and space_valid

def decode_bit(pulse, space):
    """Decode a single bit based on pulse and space durations"""
    # For this Midea protocol, it appears to use pulse width modulation:
    # Short pulse = 0, Long pulse = 1
    
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

def decode_midea_command(bits_str):
    """Decode Midea AC command from bit string"""
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
        # Enhanced Midea AC command structure analysis
        print(f"\n--- Detailed Command Analysis ---")
        print(f"Byte 0 (Command): 0x{bytes_data[0]:02X} - Power: {decode_midea_power(bytes_data[0])}")
        print(f"Byte 1 (Mode/Temp): 0x{bytes_data[1]:02X} - Mode: {decode_midea_mode(bytes_data[1])}, Temp: {decode_midea_temperature(bytes_data[1])}°C")
        print(f"Byte 2 (Fan/Swing): 0x{bytes_data[2]:02X} - Fan: {decode_midea_fan_speed(bytes_data[2])}, Swing: {decode_midea_swing(bytes_data[2])}")
        print(f"Byte 3 (Extra): 0x{bytes_data[3]:02X}")
        print(f"Byte 4 (Timer/Extra): 0x{bytes_data[4]:02X}")
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

def decode_midea_temperature(byte_val):
    """Decode temperature from Midea command byte"""
    # Midea temperature encoding varies by model, common patterns:
    temp_mappings = {
        0x00: 16, 0x01: 17, 0x02: 18, 0x03: 19, 0x04: 20,
        0x05: 21, 0x06: 22, 0x07: 23, 0x08: 24, 0x09: 25,
        0x0A: 26, 0x0B: 27, 0x0C: 28, 0x0D: 29, 0x0E: 30
    }
    
    # Extract temperature bits (usually lower 4 bits)
    temp_bits = byte_val & 0x0F
    return temp_mappings.get(temp_bits, f"Unknown ({temp_bits})")

def decode_midea_mode(byte_val):
    """Decode AC mode from Midea command byte"""
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
    """Decode fan speed from Midea command byte"""
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
    """Decode swing settings from Midea command byte"""
    swing_vertical = (byte_val >> 4) & 0x01
    swing_horizontal = (byte_val >> 5) & 0x01
    
    swing_status = []
    if swing_vertical:
        swing_status.append("Vertical")
    if swing_horizontal:
        swing_status.append("Horizontal")
    
    return " + ".join(swing_status) if swing_status else "Off"

def decode_midea_power(byte_val):
    """Decode power state from Midea command byte"""
    power_bit = (byte_val >> 5) & 0x01
    return "On" if power_bit else "Off"

import csv
import re

def import_from_csv(filename):
    """Import timing data from logic analyzer CSV export"""
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

def print_import_instructions():
    """Print instructions for importing data from logic analyzers"""
    print("""
=== Logic Analyzer Import Instructions ===

1. SALEAE LOGIC:
   - Capture your IR signal on any digital channel
   - Go to Data > Export Data > Export Timing/State
   - Choose CSV format
   - Save and use: durations = import_from_csv('your_file.csv')

2. SIGROK/PULSEVIEW:
   - Capture IR signal
   - File > Export > CSV
   - Use: durations = import_from_csv('your_file.csv')

3. DSLogic/DreamSourceLab:
   - Export as CSV with timing data
   - Use: durations = import_from_csv('your_file.csv')

4. GENERIC TEXT FILE:
   - Create a text file with one timing value per line (in microseconds)
   - Use: durations = import_from_text('your_file.txt')

Example usage:
# Replace the manual durations list with:
# durations = import_from_csv('ir_capture.csv')
# if durations is None:
#     print("Failed to import data, using example data")
#     durations = [4424, 4424, 560, 1690, 560, 560]  # fallback

""")

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

def export_for_esp_idf(bits_string, bytes_data, command_name, filename="midea_commands.h"):
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
        header_content += f" * Power: {decode_midea_power(bytes_data[0])}\n"
        header_content += f" * Mode: {decode_midea_mode(bytes_data[1])}\n" 
        header_content += f" * Temperature: {decode_midea_temperature(bytes_data[1])}°C\n"
        header_content += f" * Fan Speed: {decode_midea_fan_speed(bytes_data[2])}\n"
        header_content += f" * Swing: {decode_midea_swing(bytes_data[2])}\n"
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
    rmt_symbol_word_t* symbols = malloc(count * sizeof(rmt_symbol_word_t));
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

import datetime as import_datetime

# Load captured IR data from the ir_captures folder
durations = import_from_csv('ir_captures/digital.csv')
if durations is None:
    print("Failed to import data from ir_captures/digital.csv, using example data")
    durations = [4424, 4424, 560, 1690, 560, 560]  # fallback
else:
    print(f"Successfully loaded {len(durations)} timing values from ir_captures/digital.csv")

# Print import instructions if needed
# print_import_instructions()

if len(durations) < 4:
    print("Error: Need at least leader pulse, leader space, and one data bit")
    print("\nTo import timing data from logic analyzer, use:")
    print("durations = import_from_csv('your_file.csv')")
    print("or")
    print("durations = import_from_text('your_file.txt')")
    exit(1)

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
        print(f"Bit {len(bits)}: {bit} (pulse: {pulse}us, space: {space}us)")

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
    
    # Ask user for command name and export
    command_name = input("\nEnter a name for this command (e.g., 'power_on', 'heat_18c'): ").strip()
    if command_name:
        # Clean command name for C identifier
        command_name = command_name.replace(' ', '_').replace('-', '_')
        command_name = ''.join(c for c in command_name if c.isalnum() or c == '_')
        
        if command_name:
            export_for_esp_idf(analysis_bits, bytes_data, command_name)
            
            # Create template files on first export
            import os
            if not os.path.exists("midea_ir_blaster.h"):
                create_esp_idf_template()
                print("\n✓ Created ESP-IDF template files:")
                print("  - midea_ir_blaster.h (header file)")
                print("  - midea_ir_blaster.c (implementation)")
                print("  - midea_commands.h (commands definitions)")
        else:
            print("Invalid command name")
    else:
        print("Skipping export")
else:
    print(f"\nWarning: Only {len(analysis_bits)} valid bits found. Need more data for proper decoding.")
    print("\nTroubleshooting tips:")
    print("1. Check if your timing thresholds match your captured data")
    print("2. Verify the IR signal quality and capture settings")
    print("3. Make sure you're capturing the complete IR signal")

def process_multiple_files():
    """Process multiple CSV files in the ir_captures folder"""
    import os
    import glob
    
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
            
        # ... (rest of processing logic would go here)
        # For now, just show basic info
        print(f"Loaded {len(durations)} timing values from {file}")

# Add option to process multiple files
# Uncomment the next line to process multiple files:
# process_multiple_files()

# ...existing code...
# Midea AC IR Signal Decoder

This project decodes Midea air conditioner infrared signals captured via logic analyzer and exports them as C arrays for ESP32-C6 IR blaster implementation using ESP-IDF.

## IR Signal Packet Structure

### Overview
Midea AC uses a 38kHz carrier frequency with pulse-width modulation encoding. The complete packet consists of a leader sequence followed by data bits and typically includes a repeat sequence.

### Timing Parameters
```
Leader Pulse:    ~4424 μs
Leader Space:    ~4424 μs
Short Pulse:     ~560 μs (represents '0' bit)
Long Pulse:      ~1600 μs (represents '1' bit)
Data Space:      ~560 μs (between all data bits)
Repeat Space:    ~5000 μs (before repeat sequence)
```

### Packet Format
```
[Leader Pulse][Leader Space][Data Bits][Repeat Space][Repeat Sequence]
```

### Data Bit Encoding
- **'0' bit**: Short pulse (~560μs) + Short space (~560μs)
- **'1' bit**: Long pulse (~1600μs) + Short space (~560μs)

### Complete Packet Structure (96 bits total)
The Midea AC command consists of 12 bytes (96 bits) transmitted twice:

```
Byte 0: Command Type (Always 0xA1 for AC commands)
Byte 1: Power & Mode Control
Byte 2: Temperature Setting
Byte 3: Fan Speed & Swing Control
Byte 4: Additional Features
Byte 5: Checksum (XOR of bytes 0-4)
Bytes 6-11: Repeat of bytes 0-5
```

## Byte-Level Analysis

### Byte 0: Command Type
- **Value**: Always `0xA1` (10100001 binary)
- **Purpose**: Identifies this as a Midea AC command

### Byte 1: Power & Mode Control
```
Bit 7: Power State (1 = On, 0 = Off)
Bits 5-6: Operating Mode
  00 = Auto
  01 = Cool
  02 = Dry  
  03 = Fan
  04 = Heat
Bits 0-4: Reserved/Other functions
```

### Byte 2: Temperature Setting
```
Bits 0-3: Temperature value
Formula: Temperature (°C) = (Byte2 & 0x0F) + 17
Range: 17°C to 30°C (values 0x0 to 0xD)
Bits 4-7: Reserved
```

### Byte 3: Fan Speed & Swing Control
```
Bits 0-2: Fan Speed
  000 = Auto
  001 = Low
  010 = Medium
  011 = High
  111 = Silent
Bit 4: Vertical Swing (1 = On, 0 = Off)
Bit 5: Horizontal Swing (1 = On, 0 = Off)
Bits 6-7: Reserved
```

### Byte 4: Additional Features
- Timer settings, sleep mode, and other advanced features
- Often `0xFF` in basic commands

### Byte 5: Checksum
- **Calculation**: XOR of bytes 0-4
- **Purpose**: Error detection

## Example Signal Analysis

### Power On, Heat Mode, 19°C
```
Raw Bytes: A1 82 42 FF FF 5F
Binary:    10100001 10000010 01000010 11111111 11111111 01011111

Decoded:
- Byte 0 (0xA1): Command type = AC Command
- Byte 1 (0x82): Power = On (bit 7 = 1), Mode = Heat (bits 5-6 = 10)
- Byte 2 (0x42): Temperature = (0x2) + 17 = 19°C
- Byte 3 (0xFF): Fan = Silent, Swing = Vertical + Horizontal
- Byte 4 (0xFF): Additional features enabled
- Byte 5 (0x5F): Checksum
```

### Power Off
```
Raw Bytes: A1 02 42 FF FF DF
Binary:    10100001 00000010 01000010 11111111 11111111 11011111

Decoded:
- Byte 0 (0xA1): Command type = AC Command  
- Byte 1 (0x02): Power = Off (bit 7 = 0), Mode = Auto (bits 5-6 = 00)
- Byte 2 (0x42): Temperature = 19°C (retained from previous setting)
- Remaining bytes: Fan/swing settings and features
```

## Captured Commands

The following commands have been captured and decoded:

| Filename | Command | Power | Mode | Temperature | Description |
|----------|---------|-------|------|-------------|-------------|
| `auto_mode.csv` | AUTO_MODE | On | Heat | 18°C | Auto mode setting |
| `cool_mode.csv` | COOL_MODE | On | Heat | 19°C | Cool mode setting |
| `dry_mode.csv` | DRY_MODE | On | Heat | 18°C | Dry mode setting |
| `power_off.csv` | POWER_OFF | Off | Auto | 19°C | Power off command |
| `power_on.csv` | POWER_ON | On | Heat | 19°C | Power on command |
| `temp_17c.csv` | TEMP_17C | On | Heat | 17°C | Set temperature to 17°C |
| `temp_18c.csv` | TEMP_18C | On | Heat | 18°C | Set temperature to 18°C |
| `temp_19c.csv` | TEMP_19C | On | Heat | 19°C | Set temperature to 19°C |
| `temp_20c.csv` | TEMP_20C | On | Heat | 20°C | Set temperature to 20°C |
| `temp_21c.csv` | TEMP_21C | On | Heat | 21°C | Set temperature to 21°C |
| `temp_22c.csv` | TEMP_22C | On | Heat | 22°C | Set temperature to 22°C |

## Protocol Anomalies

### Mode Decoding Issues
Some captured signals show unexpected mode values:
- Files labeled "cool_mode" and "dry_mode" decode as "Heat" mode
- This suggests either:
  1. The remote was in heat mode when captured
  2. Additional bytes control the actual mode
  3. Mode bits are in a different location than expected

### Checksum Validation
Most captured signals show invalid checksums, which could indicate:
- Additional processing/encoding beyond simple XOR
- Different checksum algorithm
- Capture timing issues affecting the decoded bytes

## Usage

### Processing Captured Signals
```bash
# Process all CSV files automatically
python regenerate_commands.py

# Process individual file with interactive naming
python main.py

# Generate command summary
python command_summary.py
```

### ESP-IDF Integration
```c
#include "midea_ir_blaster.h"
#include "midea_commands.h"

// Initialize IR blaster
ir_blaster_init();

// Send power on command
send_ir_command(power_on_timing, POWER_ON_TIMING_COUNT);

// Or send using byte array
send_midea_bytes(power_on_bytes, POWER_ON_BYTES_COUNT);

// Send temperature command
send_ir_command(temp_20c_timing, TEMP_20C_TIMING_COUNT);
```

## Files Generated

- `midea_commands.h` - All decoded commands as C arrays
- `midea_ir_blaster.h` - ESP32-C6 IR blaster header
- `midea_ir_blaster.c` - ESP32-C6 RMT implementation
- `command_summary.py` - Generate usage summary
- `regenerate_commands.py` - Batch process all CSV files

## Hardware Requirements

### IR Capture
- Logic analyzer (Saleae Logic, etc.)
- IR receiver (TSOP38238 or similar)
- Midea AC remote control

### IR Transmission (ESP32-C6)
- ESP32-C6 development board
- IR LED (940nm recommended)
- Current limiting resistor (100-220Ω)
- Optional: IR LED driver circuit for increased range

## Future Improvements

1. **Protocol Verification**: Capture more diverse commands to verify byte mappings
2. **Checksum Algorithm**: Investigate the actual checksum calculation method
3. **Advanced Features**: Decode timer, sleep mode, and other advanced settings
4. **Mode Validation**: Capture confirmed cool/dry mode signals for verification
5. **Signal Optimization**: Fine-tune timing parameters for better transmission reliability

## References

- ESP-IDF RMT Documentation
- Midea AC Protocol Analysis
- IR Communication Standards (NEC, RC5, etc.)

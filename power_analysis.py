#!/usr/bin/env python3
"""
Deep analysis of Midea power commands
"""

def decode_midea_power_corrected(byte_val):
    """Corrected power state decoder"""
    # The power bit might be in a different position
    # Let's check multiple bit positions
    print(f"Analyzing byte 0x{byte_val:02X} = {byte_val:08b}")
    for bit_pos in range(8):
        bit_val = (byte_val >> bit_pos) & 0x01
        print(f"  Bit {bit_pos}: {bit_val}")

def decode_mode_corrected(byte_val):
    """Decode AC mode with better analysis"""
    print(f"Mode byte: 0x{byte_val:02X} = {byte_val:08b}")
    
    # Check different bit combinations for mode
    for start_bit in range(0, 6):
        for num_bits in range(1, 4):
            if start_bit + num_bits <= 8:
                mask = (1 << num_bits) - 1
                mode_val = (byte_val >> start_bit) & mask
                print(f"  Bits {start_bit}-{start_bit+num_bits-1}: {mode_val:0{num_bits}b} = {mode_val}")

def main():
    print("POWER COMMAND ANALYSIS")
    print("=" * 50)
    
    # Command data
    power_off = [0xA1, 0x02, 0x42, 0xFF, 0xFF, 0xDF, 0x17, 0xBF, 0x6F, 0x40, 0x00, 0x08]
    power_on = [0xA1, 0x82, 0x42, 0xFF, 0xFF, 0x5F, 0x17, 0x9F, 0x6F, 0x40, 0x00, 0x28]
    
    print("\n1. POWER OFF Command:")
    print("Byte 0 (Command):", hex(power_off[0]))
    decode_midea_power_corrected(power_off[0])
    print("Byte 1 (Mode/Temp):", hex(power_off[1]))
    decode_mode_corrected(power_off[1])
    
    print("\n2. POWER ON Command:")
    print("Byte 0 (Command):", hex(power_on[0]))
    decode_midea_power_corrected(power_on[0])
    print("Byte 1 (Mode/Temp):", hex(power_on[1]))
    decode_mode_corrected(power_on[1])
    
    print("\n3. KEY DIFFERENCES:")
    print("Main difference is in Byte 1 (Mode/Temperature byte):")
    print(f"  Power OFF: 0x02 = {0x02:08b}")
    print(f"  Power ON:  0x82 = {0x82:08b}")
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

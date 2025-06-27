/*
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

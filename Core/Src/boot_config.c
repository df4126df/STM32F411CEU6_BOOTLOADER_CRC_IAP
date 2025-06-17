/*
 * boot_config.c
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#include "boot_config.h"

uint8_t is_valid_firmware(uint32_t address) {
//    uint32_t *magic = (uint32_t *)(address + 0x1FC); // Example magic offset
//    return (*magic == VALID_APP_MAGIC);
	return 1;
}

uint32_t select_active_bank(void) {
    if (is_valid_firmware(APP_1_START_ADDR)) {
        return APP_1_START_ADDR;
    } else if (is_valid_firmware(APP_2_START_ADDR)) {
        return APP_2_START_ADDR;
    }
    return 0;
}

/*
 * boot_config.h
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#ifndef INC_BOOT_CONFIG_H_
#define INC_BOOT_CONFIG_H_

#include <stdint.h>

/* Declaring External Linker Script Symbols for access */
extern uint32_t APP_1_START;
extern uint32_t APP_2_START;
extern uint32_t APP_1_SIZE;
extern uint32_t APP_2_SIZE;

#define APP_1_START_ADDR    ((uint32_t)&APP_1_START)
#define APP_2_START_ADDR    ((uint32_t)&APP_2_START)
#define APP_1_BANK_SIZE     APP_1_SIZE
#define APP_2_BANK_SIZE		APP_2_SIZE

#define VALID_APP_MAGIC     0xDEADBEEF

uint8_t is_valid_firmware(uint32_t address);
uint32_t select_active_bank(void);

#endif /* INC_BOOT_CONFIG_H_ */

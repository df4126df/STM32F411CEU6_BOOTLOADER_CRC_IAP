/*
 * bootloader.c
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#include "stm32f4xx_hal.h"
#include "core_cm4.h"        // <-- gives access to __disable_irq, __set_MSP, etc.
#include "bootloader.h"
#include "boot_config.h"
#include "flash_utils.h"
#include <string.h>

typedef void (*app_entry_t)(void);

__attribute__((section(".iap_flags")))
volatile iap_flags_t boot_iap_flags = {
    .active_app = 1,
    .update_state = 1,
    .app1_version = 0,
    .app2_version = 0,
    .reserved = {0},
};

void jump_to_application(uint32_t address) {
    uint32_t sp = *(volatile uint32_t *)address; // Stack Pointer: App base address
    uint32_t pc = *(volatile uint32_t *)(address + 4); // Program counter: reset handler address

    // De-initialize hardware to clean state
    HAL_RCC_DeInit();
    HAL_DeInit();

    // Disable SysTick
    SysTick->CTRL = 0;
    SysTick->LOAD = 0;
    SysTick->VAL = 0;

    // Disable all interrupts
    __disable_irq();
    for (uint8_t i = 0; i < 8; i++) {
        NVIC->ICER[i] = 0xFFFFFFFF;
        NVIC->ICPR[i] = 0xFFFFFFFF;
    }

    // Set Vector Table Offset Register
    SCB->VTOR = address;

    // Set MSP (first word of application vector table)
    __set_MSP(sp);

    // Get app reset handler (second word of vector table)
    app_entry_t app_entry = (app_entry_t)pc;

    __enable_irq();

    // Jump to application
    app_entry();
}

void receive_firmware(UART_HandleTypeDef *huart, uint32_t target_app_addr){
	uint8_t rx_buf[256];
	uint32_t offset = 0;
	uint32_t firmware_size = 0;
	uint32_t timeout = 10000; // optional

	// === Wait for "OPEN" ===
	HAL_UART_Receive(huart, rx_buf, 4, timeout);
	if (memcmp(rx_buf, "OPEN", (size_t)4) != 0) {
		boot_iap_flags.update_state = 3; // ERROR
		return;
	}

	// === Receive firmware size (4 bytes, little-endian) ===
	HAL_UART_Receive(huart, rx_buf, 4, timeout);
	memcpy(&firmware_size, rx_buf, (size_t)4);
	if (firmware_size == 0 || firmware_size > 0x100000) { // sanity check
		boot_iap_flags.update_state = 3; // ERROR
		return;
	}

	// === Receive firmware data ===
	while (offset < firmware_size) {
		uint32_t chunk_size = (firmware_size - offset) > sizeof(rx_buf) ? sizeof(rx_buf) : (firmware_size - offset);

		if (HAL_UART_Receive(huart, rx_buf, chunk_size, timeout) != HAL_OK) {
			boot_iap_flags.update_state = 3; // ERROR
			return;
		}

		if (flash_write(target_app_addr + offset, rx_buf, chunk_size) != 0) {
			boot_iap_flags.update_state = 3; // ERROR
			return;
		}

		offset += chunk_size;
	}

	// === Wait for "DONE" ===
	HAL_UART_Receive(huart, rx_buf, 4, timeout);
	if (memcmp(rx_buf, "DONE", (size_t)4) != 0) {
		boot_iap_flags.update_state = 3; // ERROR
		return;
	}
}

void bootloader_run(UART_HandleTypeDef *huart) {

    // === Step 1: Handle update request ===
    if (1 /*boot_iap_flags.update_state == 1*/) {
        uint32_t target_app_addr = (boot_iap_flags.active_app == 1) ? APP_2_START : APP_1_START;
        uint32_t target_app_size = (boot_iap_flags.active_app == 1) ? APP_2_SIZE : APP_1_SIZE;

        // Erase target flash
        flash_erase(target_app_addr, target_app_size);

        // Receive firmware chunks over UART/SPI/etc.
        receive_firmware(huart, target_app_addr);

        // [Optional] CRC check goes here

        if (boot_iap_flags.update_state == 2) {
			// Update metadata: switch active app, mark update complete
			boot_iap_flags.active_app = (boot_iap_flags.active_app == 1) ? 2 : 1;
			boot_iap_flags.update_state = 2;  // Mark as done

			// Write back updated flags (reflash flags section)
			HAL_FLASH_Unlock();
			flash_write((uint32_t)&boot_iap_flags, (uint8_t *)&boot_iap_flags, sizeof(boot_iap_flags));
			HAL_FLASH_Lock();
        } else {
        	// Optional: log or blink LED to indicate failed update
        }
    }

    // === Step 2: Jump to selected app ===
    uint32_t app_addr = select_active_bank();
    if (app_addr) {
        jump_to_application(app_addr);
    }

    // Optionally blink LED or go to fail-safe mode
    while (1);
}

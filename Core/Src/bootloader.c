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

typedef void (*app_entry_t)(void);

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

void bootloader_run(void) {
    uint32_t app_addr = select_active_bank();
    if (app_addr) {
        jump_to_application(app_addr);
    }

    // Optionally blink LED or go to fail-safe mode
    while (1);
}

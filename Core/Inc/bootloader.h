/*
 * bootloader.h
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#ifndef INC_BOOTLOADER_H_
#define INC_BOOTLOADER_H_

#include <stdint.h>

typedef struct {
    uint32_t active_app;     // 1 = APP_1 active, 2 = APP_2 active
    uint32_t update_state;   // e.g. 0 = idle, 1 = updating, 2 = done, 3 = error
    uint32_t app1_version;
    uint32_t app2_version;
    uint32_t reserved[4];    // Reserved for future use
} iap_flags_t;

extern volatile iap_flags_t boot_iap_flags;

void jump_to_application(uint32_t address);
void receive_firmware(UART_HandleTypeDef *huart, uint32_t target_app_addr);
void bootloader_run(UART_HandleTypeDef *huart);

#endif /* INC_BOOTLOADER_H_ */

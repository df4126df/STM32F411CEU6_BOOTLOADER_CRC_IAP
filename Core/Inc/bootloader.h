/*
 * bootloader.h
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#ifndef INC_BOOTLOADER_H_
#define INC_BOOTLOADER_H_

#include <stdint.h>

void jump_to_application(uint32_t address);
void bootloader_run(void);

#endif /* INC_BOOTLOADER_H_ */

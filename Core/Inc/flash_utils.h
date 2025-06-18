/*
 * flash_utils.h
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#ifndef INC_FLASH_UTILS_H_
#define INC_FLASH_UTILS_H_

#include <stdint.h>

int flash_erase(uint32_t start_addr, uint32_t size);
int flash_write(uint32_t addr, const uint8_t *data, uint32_t len);
int flash_read(uint32_t addr, uint8_t *buffer, uint32_t len);

#endif /* INC_FLASH_UTILS_H_ */

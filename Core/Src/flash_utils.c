/*
 * flash_utils.c
 *
 *  Created on: May 31, 2025
 *      Author: delors
 */

#include "flash_utils.h"
#include "stm32f4xx_hal.h"

int flash_erase(uint32_t start_addr, uint32_t size) {
    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef erase;
    uint32_t page_error = 0;
    erase.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    erase.Sector = FLASH_SECTOR_2; // Update based on start_addr
    erase.NbSectors = 4; // Update based on size

    if (HAL_FLASHEx_Erase(&erase, &page_error) != HAL_OK) {
        HAL_FLASH_Lock();
        return -1;
    }

    HAL_FLASH_Lock();
    return 0;
}

int flash_write(uint32_t addr, const uint8_t *data, uint32_t len) {
    HAL_FLASH_Unlock();
    for (uint32_t i = 0; i < len; i += 4) {
        uint32_t word = *(uint32_t *)(data + i);
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr + i, word) != HAL_OK) {
            HAL_FLASH_Lock();
            return -1;
        }
    }
    HAL_FLASH_Lock();
    return 0;
}

int flash_read(uint32_t addr, uint8_t *buffer, uint32_t len) {
    for (uint32_t i = 0; i < len; i++) {
        buffer[i] = *(volatile uint8_t *)(addr + i);
    }
    return 0;
}

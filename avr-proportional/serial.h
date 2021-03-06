/*
 * ----------------------------------------------------------------------------
 * "THE BEER-WARE LICENSE" (Revision 42):
 * <joerg@FreeBSD.ORG> wrote this file.  As long as you retain this notice you
 * can do whatever you want with this stuff. If we meet some day, and you think
 * this stuff is worth it, you can buy me a beer in return.        Joerg Wunsch
 * ----------------------------------------------------------------------------
 *
 *  Adapted 20 Jun 2006    for Flaming Lotus Girls
 */
#ifndef SERIAL_H
#define SERIAL_H

#include <stdio.h>

/*
 * Perform UART startup initialization.
 */
void	uart_init(void);

/*
 * Send one character to the UART.
 */
int	uart_putchar(char c, FILE *unused);

/* 
 * print string to uart
 * Really should do proper printf formatting, but fuck it.
 */
#define dprintf(debugStr) 
// serialPrintf(debugStr)

void serialPrintf(const char *str);

void enable_serial_interrupts(void);
#endif //SERIAL_H



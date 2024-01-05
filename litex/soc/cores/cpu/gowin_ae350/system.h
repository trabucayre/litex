#ifndef __SYSTEM_H
#define __SYSTEM_H

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((unused)) static void flush_cpu_icache(void){};
__attribute__((unused)) static void flush_cpu_dcache(void){};
void flush_l2_cache(void);

void busy_wait(unsigned int ms);
void busy_wait_us(unsigned int us);

#include <stdint.h>

// FIXME
#define CSR_UART_BASE
#define UART_POLLING

#define _IO_(addr)              (addr)
#define __I                     volatile const  /* 'read only' permissions      */
#define __O                     volatile        /* 'write only' permissions     */
#define __IO                    volatile        /* 'read / write' permissions   */

typedef struct
{   
    __I  unsigned int IDREV;        /* 0x00 ID and Revision Register          */
         unsigned int RESERVED0[3]; /* 0x04~0x0C Reserved                     */
    __I  unsigned int CFG;          /* 0x10 Hardware Configure Register       */
    __IO unsigned int OSCR;         /* 0x14 Over Sample Control Register      */
         unsigned int RESERVED1[2]; /* 0x18~0x1C Reserved                     */
    union
    {
        __I  unsigned int RBR;      /* 0x20 Receiver Buffer Register          */
        __O  unsigned int THR;      /* 0x20 Transmitter Holding Register      */
        __IO unsigned int DLL;      /* 0x20 Divisor Latch LSB                 */
    };
    union
    {
        __IO unsigned int IER;      /* 0x24 Interrupt Enable Register         */
        __IO unsigned int DLM;      /* 0x24 Divisor Latch MSB                 */
    };
    union
    {
        __I  unsigned int IIR;      /* 0x28 Interrupt Identification Register */
        __O  unsigned int FCR;      /* 0x28 FIFO Control Register             */
    };
    __IO unsigned int LCR;          /* 0x2C Line Control Register             */
    __IO unsigned int MCR;          /* 0x30 Modem Control Register            */
    __IO unsigned int LSR;          /* 0x34 Line Status Register              */
    __IO unsigned int MSR;          /* 0x38 Modem Status Register             */
    __IO unsigned int SCR;          /* 0x3C Scratch Register                  */
} UART_RegDef;

#define UART2_BASE              _IO_(0xF0300000)    /* UART2 */
#define AE350_UART2             ((UART_RegDef *) UART2_BASE ) /* UART2 */

static inline char uart_txfull_read(void);
static inline char uart_rxempty_read(void);
static inline void uart_ev_enable_write(char c);
static inline void uart_rxtx_write(char c);
static inline char uart_rxtx_read(void);
static inline void uart_ev_pending_write(char);
static inline char uart_ev_pending_read(void);

static inline char uart_txfull_read(void) {
  return !(AE350_UART2->LSR & (1 << 5));
}

static inline char uart_rxempty_read(void) {
  return !(AE350_UART2->LSR & 0b1);
}

static inline void uart_ev_enable_write(char c) {
  // FIXME
}

static inline void uart_rxtx_write(char c) {
  AE350_UART2->THR = (uint32_t) c;
}

static inline char uart_rxtx_read(void)
{
  return (char)(AE350_UART2->RBR);
}

static volatile uint8_t is_init = 0;

#define UCLKFREQ (50 * 1000000)
#define BAUD_RATE(n) ((UCLKFREQ + 8 * (n)) / (16 * (n)))

static inline void uart_ev_pending_write(char x) {
	if (is_init !=0)
		return;
	is_init = 1;
	unsigned int baudrate = 115200;


	/* Set DLAB to 1 */
    AE350_UART2->LCR |= 0x80;

    /* Set DLL for baud rate */
    AE350_UART2->DLL = (BAUD_RATE(baudrate) >> 0) & 0xff;
    AE350_UART2->DLM = (BAUD_RATE(baudrate) >> 8) & 0xff;

    /* LCR: length 8, no parity, 1 stop bit. */
    AE350_UART2->LCR = 0x03;

    /* FCR: enable FIFO, reset TX and RX. */
    AE350_UART2->FCR = 0x07;

}
static inline char uart_ev_pending_read(void) {
  return 0;
}


#ifdef __cplusplus
}
#endif

#endif /* __SYSTEM_H */

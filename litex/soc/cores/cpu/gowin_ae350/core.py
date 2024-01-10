#
# This file is part of LiteX.
#
# Copyright (c) 2021 Ilia Sergachev <ilia.sergachev@protonmail.ch>
# Copyright (c) 2021 Gwenhael Goavec-Merou <gwenhael@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import os

from migen import *

from litex.gen import *

from litex.soc.interconnect import wishbone, ahb
from litex.soc.interconnect.csr import *
from litex.soc.cores.cpu import CPU, CPU_GCC_TRIPLE_RISCV32

# Gowin AE350 --------------------------------------------------------------------------------------

class GowinAE350(CPU):
    variants             = ["standard"]
    category             = "hardcore"
    family               = "riscv"
    name                 = "gowin_ae350"
    human_name           = "Gowin AE350"
    data_width           = 32
    endianness           = "little"
    reset_address        = 0x8000_0000
    gcc_triple           = CPU_GCC_TRIPLE_RISCV32
    linker_output_format = "elf32-littleriscv"
    nop                  = "nop"
    io_regions           = {
        # Origin, Length.
        0xe800_0000: 0x6000_0000
    }

    @property
    def mem_map(self):
        return {
            "rom"         : 0x80000000,
            "sram"        : 0x00000000, # DDR/SDRAM Data Memory
            #"sram"        : 0xa0200000, # DLM
            "peripherals" : 0xf0000000,
            "csr"         : 0xe8000000,
        }

    # GCC Flags.
    @property
    def gcc_flags(self):
        #flags =  f" -mabi=ilp32 -march=rv32imafdc"
        flags =  f" -mabi=ilp32 -march=rv32i2p0"
        flags += f" -D__AE350__"
        flags += f" -DUART_POLLING"
        return flags

    def __init__(self, platform, variant, *args, **kwargs):
        self.platform       = platform
        self.reset          = Signal()
        self.ibus           = ibus = wishbone.Interface(data_width=32, address_width=32, addressing="byte")
        self.dbus           = dbus = wishbone.Interface(data_width=64, address_width=32, addressing="word")
        self.pbus           = pbus = wishbone.Interface(data_width=32, address_width=32, addressing="byte")
        self.periph_buses   = [ibus, dbus, pbus] # Peripheral buses (Connected to main SoC's bus).
        self.memory_buses   = []                 # Memory buses (Connected directly to LiteDRAM).

        # CPU Instance.
        # -------------

        self.ahb_ddr   = ahb_ddr   = ahb.AHBInterface(data_width=64, address_width=32)
        self.ahb_flash = ahb_flash = ahb.AHBInterface(data_width=32, address_width=32)
        ahb_exts       = ahb.AHBInterface(data_width=32, address_width=32)
        self.presetn   = Signal()
        self.hresetn   = Signal()
        self.ddr_rstn  = Signal()
        self.core_rstn = Signal()

        self._inv_rst = CSRStorage()

        self.comb += [
            ahb_flash.sel.eq(1),
            ahb_ddr.sel.eq(1),
            ahb_flash.size.eq(0b010),
            ahb_flash.burst.eq(0),
            If(~self._inv_rst.storage[0],
                self.core_rstn.eq(~(ResetSignal("sys") | self.reset)),
            ).Else(
                self.core_rstn.eq((ResetSignal("sys") | self.reset)),
            ),
        ]

        self.ddr_hrdata = Signal(64)
        self.ddr_hready = Signal()
        self.ddr_hresp  = Signal()
        self.ddr_haddr  = Signal(32)
        self.ddr_hburst = Signal(3)
        self.ddr_hsize  = Signal(3)
        self.ddr_hprot  = Signal(4)
        self.ddr_htrans = Signal(2)
        self.ddr_hwdata = Signal(64)
        self.ddr_hwrite = Signal()

        self.cpu_params = dict(
            # Clk/Rst.
            i_CORE_CLK       = ClockSignal("mcu"),
            i_DDR_CLK        = ClockSignal("sys"),
            i_AHB_CLK        = ClockSignal("sys"),
            i_APB_CLK        = ClockSignal("sys"),
            i_POR_N          = 1,
            i_HW_RSTN        = self.core_rstn, #~(ResetSignal("sys") | self.reset),
            o_PRESETN        = self.presetn,   # apb_clk_in synced reset_n output
            o_HRESETN        = self.hresetn,   # ahb_clk_in synced reset_n output
            o_DDR_RSTN       = self.ddr_rstn,  # ddr_clk_in synced reset_n output

            # CE.
            i_CORE_CE        = 1,
            i_AXI_CE         = 1,
            i_DDR_CE         = 1,
            i_AHB_CE         = 1,
            i_APB_CE         = Constant(0b10100101, 8), # WDT, I2C, PIT, GPIO, SPI, UART2, UART1, APB
            i_APB2AHB_CE     = 1, # 1 when apb_clk_in = ahb_clk_in

            # WFI.
            o_CORE0_WFI_MODE = Open(),
            i_WAKEUP_IN      = 0, # input to wake up CPU, 0 is wake up

            # RTC.
            i_RTC_CLK        = ClockSignal("rtc"),
            o_RTC_WAKEUP     = Open(),

            # Interrupts.
            i_GP_INT         = Constant(0, 16),

            # DMA.
            i_DMA_REQ        = Constant(0, 8),
            o_DMA_ACK        = Open(8),

            # AHB port for ROM.
            i_ROM_HRDATA     = ahb_flash.rdata,
            i_ROM_HREADY     = ahb_flash.readyout,
            i_ROM_HRESP      = ahb_flash.resp,
            o_ROM_HADDR      = ahb_flash.addr,
            o_ROM_HTRANS     = ahb_flash.trans,
            o_ROM_HWRITE     = ahb_flash.write,

            # APB PORT FOR FABRIC.
            o_APB_PADDR      = Open(32),
            o_APB_PENABLE    = Open(),
            i_APB_PRDATA     = Constant(0, 32),
            i_APB_PREADY     = 0,
            o_APB_PSEL       = Open(),
            o_APB_PWDATA     = Open(32),
            o_APB_PWRITE     = Open(),
            i_APB_PSLVERR    = 0,
            o_APB_PPROT      = Open(3),
            o_APB_PSTRB      = Open(4),

            # EXT AHB slv port (MCU bus is master).
            i_EXTS_HRDATA    = ahb_exts.rdata,
            i_EXTS_HREADYIN  = ahb_exts.readyout,
            i_EXTS_HRESP     = ahb_exts.resp,
            o_EXTS_HADDR     = ahb_exts.addr,
            o_EXTS_HBURST    = ahb_exts.burst,
            o_EXTS_HPROT     = ahb_exts.prot,
            o_EXTS_HSEL      = ahb_exts.sel,
            o_EXTS_HSIZE     = ahb_exts.size,
            o_EXTS_HTRANS    = ahb_exts.trans,
            o_EXTS_HWDATA    = ahb_exts.wdata,
            o_EXTS_HWRITE    = ahb_exts.write,

            # EXT AHB MST PORT(MCU BUS IS SLAVE).
            i_EXTM_HADDR     = Constant(0, 32),
            i_EXTM_HBURST    = Constant(0, 3),
            i_EXTM_HPROT     = Constant(0, 4),
            o_EXTM_HRDATA    = Open(64),
            i_EXTM_HREADY    = 0,
            o_EXTM_HREADYOUT = Open(),
            o_EXTM_HRESP     = Open(),
            i_EXTM_HSEL      = 0,
            i_EXTM_HSIZE     = Constant(0, 3),
            i_EXTM_HTRANS    = Constant(0, 2),
            i_EXTM_HWDATA    = Constant(0, 64),
            i_EXTM_HWRITE    = 0,

            # SDRAM port for Fabric.
            i_DDR_HRDATA     = self.ddr_hrdata,
            i_DDR_HREADY     = self.ddr_hready,
            i_DDR_HRESP      = self.ddr_hresp,
            o_DDR_HADDR      = self.ddr_haddr,
            o_DDR_HBURST     = self.ddr_hburst,
            o_DDR_HPROT      = self.ddr_hprot,
            o_DDR_HSIZE      = self.ddr_hsize,
            o_DDR_HTRANS     = self.ddr_htrans,
            o_DDR_HWDATA     = self.ddr_hwdata,
            o_DDR_HWRITE     = self.ddr_hwrite,

            # GPIOs.
            i_GPIO_IN        = Constant(0, 32),
            o_GPIO_OUT       = Open(32),
            o_GPIO_OE        = Open(32),

            i_SCAN_EN        = 0,
            i_SCAN_TEST      = 0,
            i_SCAN_IN        = Constant(0xfffff, 20),
            o_SCAN_OUT       = Open(20),
            i_INTEG_TCK      = 1,
            i_INTEG_TDI      = 1,
            i_INTEG_TMS      = 1,
            i_INTEG_TRST     = 1,
            o_INTEG_TDO      = Open(),

            # SRAM?.
            i_PGEN_CHAIN_I   = 1,
            o_PRDYN_CHAIN_O  = Open(),
            i_EMA            = Constant(0b011, 3),
            i_EMAW           = Constant(0b01, 2),
            i_EMAS           = 0,
            i_RET1N          = 1,
            i_RET2N          = 1,

            # SPI2.
            i_SPI2_HOLDN_IN  = 0,
            i_SPI2_WPN_IN    = 0,
            i_SPI2_CLK_IN    = 0,
            i_SPI2_CSN_IN    = 0,
            i_SPI2_MISO_IN   = 0,
            i_SPI2_MOSI_IN   = 0,
            o_SPI2_HOLDN_OUT = Open(),
            o_SPI2_HOLDN_OE  = Open(),
            o_SPI2_WPN_OUT   = Open(),
            o_SPI2_WPN_OE    = Open(),
            o_SPI2_CLK_OUT   = Open(),
            o_SPI2_CLK_OE    = Open(),
            o_SPI2_CSN_OUT   = Open(),
            o_SPI2_CSN_OE    = Open(),
            o_SPI2_MISO_OUT  = Open(),
            o_SPI2_MISO_OE   = Open(),
            o_SPI2_MOSI_OUT  = Open(),
            o_SPI2_MOSI_OE   = Open(),

            # I2C.
            i_I2C_SCL_IN     = 0,
            i_I2C_SDA_IN     = 0,
            o_I2C_SCL        = Open(),
            o_I2C_SDA        = Open(),

            # PIT/PWM.
            o_CH0_PWM        = Open(),
            o_CH0_PWMOE      = Open(),
            o_CH1_PWM        = Open(),
            o_CH1_PWMOE      = Open(),
            o_CH2_PWM        = Open(),
            o_CH2_PWMOE      = Open(),
            o_CH3_PWM        = Open(),
            o_CH3_PWMOE      = Open(),

            # UART1.
            o_UART1_TXD      = Open(),
            o_UART1_RTSN     = Open(),
            i_UART1_RXD      = 0,
            i_UART1_CTSN     = 0,
            i_UART1_DSRN     = 0,
            i_UART1_DCDN     = 0,
            i_UART1_RIN      = 0,
            o_UART1_DTRN     = Open(),
            o_UART1_OUT1N    = Open(),
            o_UART1_OUT2N    = Open(),

            o_UART2_TXD      = Open(),
            o_UART2_RTSN     = Open(),
            i_UART2_RXD      = 0,
            i_UART2_CTSN     = 1,
            i_UART2_DCDN     = 1,
            i_UART2_DSRN     = 1,
            i_UART2_RIN      = 1,
            o_UART2_DTRN     = Open(),
            o_UART2_OUT1N    = Open(),
            o_UART2_OUT2N    = Open(),
            
            # Test
            i_TEST_CLK       = 0,
            i_TEST_MODE      = 0,
            i_TEST_RSTN      = 1,
        )

        # DDR.
        # ----

        USE_SRAM_MODEL = 3
        if USE_SRAM_MODEL in [1, 2]:
            self.comb += [
                self.ddr_hrdata.eq(ahb_ddr.rdata),
                ahb_ddr.readyout.eq(self.ddr_hready),
                ahb_ddr.resp.eq(self.ddr_hresp),
                self.ddr_haddr.eq(ahb_ddr.addr),
                self.ddr_hburst.eq(ahb_ddr.burst),
                self.ddr_hprot.eq(ahb_ddr.prot),
                self.ddr_hsize.eq(ahb_ddr.size),
                self.ddr_htrans.eq(ahb_ddr.trans),
                self.ddr_hwdata.eq(ahb_ddr.wdata),
                self.ddr_hwrite.eq(ahb_ddr.write),
            ]
            if USE_SRAM_MODEL == 1:
                self.ram_bus = ram_bus = wishbone.Interface(
                    data_width    = 64,
                    address_width = 32,
                    addressing    = "word"
                )
                self.ram = ram = wishbone.SRAM(2*64*1024,
                    bus       = ram_bus,
                    read_only = False,
                    name      = "cpu_ram"
                )
                self.add_module(name="cpu_ram", module=ram)
                self.submodules += ahb.AHB2Wishbone(ahb_ddr, ram_bus)
            else:
                self.submodules += ahb.AHB2Wishbone(ahb_ddr, self.dbus)
        elif USE_SRAM_MODEL == 3:
            dlm_params = dict(
                i_HCLK     = ClockSignal("sys"),
                i_HRESETn  = self.ddr_rstn,
                i_HTRANS   = self.ddr_htrans,
                i_HSIZE    = self.ddr_hsize,
                i_HWRITE   = self.ddr_hwrite,
                i_HADDR    = self.ddr_haddr,
                i_HWDATA   = self.ddr_hwdata,
                o_HREADYOUT= self.ddr_hready,
                o_HRESP    = self.ddr_hresp,
                o_HRDATA   = self.ddr_hrdata,
                # burst, prot unused
            )

            self.specials += Instance("gw_ahb_dlm_top", **dlm_params)
            curr_dir = os.getcwd()
            sources  = ["gw_ahb_dlm_config.v", "gw_ahb_dlm_top.v", "gw_ahb_dlm.v"]
            for s in sources:
                os.system(f"wget www.trabucayre.com/gw_ahb_dlm/{s}")
            for s in sources:
                self.platform.add_source(os.path.join(curr_dir, s))
        else:
            self.comb += [
                self.ddr_hready.eq(0),
                self.ddr_hresp.eq(0),
                self.ddr_hrdata.eq(0),
            ]

        # Flash (Boot Flash memory connected via AHB).
        # --------------------------------------------

        self.submodules += ahb.AHB2Wishbone(ahb_flash, self.ibus)

        # Extension AHB -> Wishbone CSR via bridge.
        # -----------------------------------------

        self.submodules += ahb.AHB2Wishbone(ahb_exts, self.pbus)

    def connect_uart(self, pads, n=0):
        assert n in (0, 1), "this CPU has 2 built-in UARTs, 0 and 1"
        n += 1
        self.uart_tx = Signal()
        self.comb += self.uart_tx.eq(pads.tx)
        self.cpu_params.update({
            f"i_UART{n}_RXD": pads.rx,
            f"o_UART{n}_TXD": pads.tx
        })

    def connect_jtag(self, pads):
        self.cpu_params.update(
            i_DBG_TCK = pads.tck,
            i_TMS_IN  = pads.tms,
            i_TRST_IN = pads.trst,
            i_TDI_IN  = pads.tdi,
            o_TDO_OUT = pads.tdo,
            o_TDO_OE  = Open(),
        )

    def do_finalize(self):
        self.specials += Instance("AE350_SOC", **self.cpu_params)

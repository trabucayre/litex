#
# This file is part of LiteX.
#
# This file is Copyright (c) 2022 Gwenhael Goavec-Merou <gwenhael.goavec-merou@trabucayre.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import shutil

from litex.build.tools import write_to_file
from litex.soc.software import PackageLibrary

# libXil library package ---------------------------------------------------------------------------

class LibXil(PackageLibrary):
    """
    LibXil class (PackageLibrary subclass) dedicated for Zynq7000/ZynqMP
    software library

    Attributes
    ==========
    _libxil_path: str
        embeddedsw directory path
    """
    def __init__(self, softwaredir, includedir, srcdir=None):
        """ CTOR

        Parameters
        ==========
        softwaredir: str
            software path
        includedir: str
            include directory path
        srcdir: str
            directory path where Makefile is located
        """
        self._libxil_path = os.path.join(softwaredir, 'libxil')
        PackageLibrary.__init__(self, "libxil", softwaredir, includedir)


    def prepare_software(self):
        """ Creates software directory and clone embeddedsw repository
        """
        os.makedirs(os.path.realpath(self._libxil_path), exist_ok=True)
        lib = os.path.join(self._libxil_path, 'embeddedsw')
        if not os.path.exists(lib):
            os.system("git clone --depth 1 https://github.com/Xilinx/embeddedsw {}".format(lib))

        for header in [
            'XilinxProcessorIPLib/drivers/uartps/src/xuartps_hw.h',
            'lib/bsp/standalone/src/common/xil_types.h',
            'lib/bsp/standalone/src/common/xil_assert.h',
            'lib/bsp/standalone/src/common/xil_io.h',
            'lib/bsp/standalone/src/common/xil_printf.h',
            'lib/bsp/standalone/src/common/xstatus.h',
            'lib/bsp/standalone/src/common/xdebug.h',
            'lib/bsp/standalone/src/arm/cortexa9/xpseudo_asm.h',
            'lib/bsp/standalone/src/arm/cortexa9/xreg_cortexa9.h',
            'lib/bsp/standalone/src/arm/cortexa9/xil_cache.h',
            'lib/bsp/standalone/src/arm/cortexa9/xparameters_ps.h',
            'lib/bsp/standalone/src/arm/cortexa9/xil_errata.h',
            'lib/bsp/standalone/src/arm/cortexa9/xtime_l.h',
            'lib/bsp/standalone/src/arm/common/xil_exception.h',
            'lib/bsp/standalone/src/arm/common/gcc/xpseudo_asm_gcc.h',
        ]:
            shutil.copy(os.path.join(lib, header), self._include_dir)

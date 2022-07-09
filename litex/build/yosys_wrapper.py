#
# This file is part of LiteX.
#
# Copyright (c) 2022 Gwenhael Goavec-Merou <gwenhael.goavec-merou@trabucayre.com>
# SPDX-License-Identifier: BSD-2-Clause


from litex.build import tools


class YosysWrapper():
    """
    YosysWrapper synthesis wrapper
    """

    def __init__(self, platform, build_name,
            nowidelut=False, abc9 = False, yosys_opts="",
            yosys_cmd=[], synth_format="json"):
        """
        Parameters
        ==========
        platform : GenericPlatform subclass
            current platform.
        build_name : str
            gateware name.
        nowidelut : bool
            do not use PFU muxes to implement LUTs larger than LUT4s.
        abc9 : bool
            use new ABC9 flow.
        yosys_opts : str
            Yosys options to use for synth_xxx
        yosys_cmd : list
            optionals commands called befor synth_xxx
        synth_format : str
            Yosys ouptput format
        """
        self._platform = platform
        self._build_name = build_name
        self._synth_format = synth_format
        self._yosys_opts = yosys_opts
        self._yosys_cmd = yosys_cmd

        if platform.device.startswith("ice40"):
            self._target="ice40"
        elif platform.device.startswith("LFE5"):
            self._target="ecp5"
        elif platform.device.startswith("LIFC"):
            self._target="nexus"
        else:
            raise ValueError(f"Invalid device family {platform.device}")

        self._yosys_opts += " -nowidelut" if nowidelut else ""
        self._yosys_opts += " -abc9" if abc9 else ""

    def common_yosys_import_sources(self):
        """built a list of sources to read
        Return
        ======
            a string containing all read_xxx lines
        """
        includes = ""
        reads = []
        for path in self._platform.verilog_include_paths:
            includes += " -I" + path
        for filename, language, library, *copy in self._platform.sources:
            # yosys has no such function read_systemverilog
            if language == "systemverilog":
                language = "verilog -sv"
            reads.append(f"read_{language}{includes} {filename}")
        return "\n".join(reads)

    def build_script(self):
        """fill and write ys script.
        """
        ys = [
            "verilog_defaults -push",
            "verilog_defaults -add -defer",
            self.common_yosys_import_sources(),
            "verilog_defaults -pop",
            "attrmap -tocase keep -imap keep=\"true\" "
                     "keep=1 -imap keep=\"false\" keep=0 -remove keep=0",
        ]
        if self._yosys_cmd != []:
            ys.append("\n".join(self._yosys_cmd))
        ys.append(f"synth_{self._target} {self._yosys_opts} "
            f" -{self._synth_format} {self._build_name}.{self._synth_format}"
            f" -top {self._build_name}")
        tools.write_to_file(self._build_name + ".ys", "\n".join(ys))

    def get_yosys_call(self, target="script"):
        """built the script command or Makefile rule + command

        Parameters
        ==========
        target : str
            selects if it's a script command or a Makefile rule to be returned

        Returns
        =======
        str containing instruction and/or rule
        """
        base_cmd = f"yosys -l {self._build_name}.rpt {self._build_name}.ys\n"
        if target == "makefile":
            return f"{self._build_name}.{self._synth_format}:\n\t" + base_cmd
        elif target == "script":
            return base_cmd
        else:
            raise ValueError("Invalid script type")

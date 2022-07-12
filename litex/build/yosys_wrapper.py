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

    def __init__(self, platform, build_name, output_name="",
            template=[], yosys_opts="",
            yosys_pre_cmds=[], yosys_pre_synth_cmds=[],
            yosys_post_synth_cmds=[], synth_format="json",
            **kwargs):
        """
        Parameters
        ==========
        platform : GenericPlatform subclass
            current platform.
        build_name : str
            gateware name.
        output_name: str
            optional output name if different to build_name
        templace: str
            yosys template to use instead of default.
        yosys_opts : str
            Yosys options to use for synth_xxx
        yosys_pre_cmds : list
            optionals commands to calls at the script begin.
        yosys_pre_synth_cmds : list
            optionals commands called before synth_xxx
        yosys_pre_synth_cmds : list
            optionals commands called after synth_xxx
        synth_format : str
            Yosys ouptput format
        kwargs: dict
            list of key/value for yosys_opts
        """

        self._template = self._default_template if template == [] else template
        self._output_name = build_name if output_name == "" else output_name

        self._platform = platform
        self._build_name = build_name
        self._synth_format = synth_format
        self._yosys_opts = yosys_opts
        self._yosys_pre_cmds = yosys_pre_cmds
        self._yosys_pre_synth_cmds = yosys_pre_synth_cmds
        self._yosys_post_synth_cmds = yosys_post_synth_cmds

        if platform.device.startswith("ice40"):
            self._target="ice40"
        elif platform.device.startswith("LFE5"):
            self._target="ecp5"
        elif platform.device.startswith("LIFC"):
            self._target="nexus"
        else:
            raise ValueError(f"Invalid device family {platform.device}")

        for key,value in kwargs.items():
            key = key.replace("_","-")
            if isinstance(value, bool):
                self._yosys_opts += f"-{key} " if value else ""
            else:
                self._yosys_opts += f"-{key} {value} "

    def _import_sources(self):
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

    _default_template = [
        "{yosys_pre_cmds}",
        "verilog_defaults -push",
        "verilog_defaults -add -defer",
        "{read_files}",
        "verilog_defaults -pop",
        "attrmap -tocase keep -imap keep=\"true\" keep=1 -imap keep=\"false\" keep=0 -remove keep=0",
        "{yosys_pre_synth_cmds}",
        "synth_{target} {synth_opts} -{synth_fmt} {output_name}.{synth_fmt} -top {build_name}",
        "{yosys_post_synth_cmds}",
    ]

    def build_script(self):
        """fill and write ys script.
        """
        read_files = self._import_sources()
        yosys_pre_cmds = "\n".join(self._yosys_pre_cmds)
        yosys_pre_synth_cmds = []
        for l in self._yosys_pre_synth_cmds:
            yosys_pre_synth_cmds.append(l.format(
                build_name = self._build_name,
                read_files = read_files,
                synth_opts = self._yosys_opts,
                target     = self._target,
                synth_fmt  = self._synth_format,
            ))
        yosys_pre_synth_cmds = "\n".join(yosys_pre_synth_cmds)
        yosys_post_synth_cmds = "\n".join(self._yosys_post_synth_cmds)
        ys = []
        for l in self._template:
            ys.append(l.format(
                build_name            = self._build_name,
                read_files            = read_files,
                synth_opts            = self._yosys_opts,
                yosys_pre_cmds        = yosys_pre_cmds,
                yosys_pre_synth_cmds  = yosys_pre_synth_cmds,
                yosys_post_synth_cmds = yosys_post_synth_cmds,
                target                = self._target,
                synth_fmt             = self._synth_format,
                output_name           = self._output_name,
            ))

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

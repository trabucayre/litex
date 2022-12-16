#
# This file is part of LiteX.
#
# This file is Copyright (c) 2022 Gwenhael Goavec-Merou <gwenhael.goavec-merou@trabucayre.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import inspect
import importlib
import subprocess

# library package (Generic) ------------------------------------------------------------------------

class PackageLibrary:
    """
    Generic class for LiteX libraries, handle directory creation
    (prepare_software), building library (build_software)
    Libraries must be retrieved using get_library_inst to instanciates
    the corresponding subclass or PackageLibrary where no specifics class
    is present.

    Attributes
    ==========
    _library_name: str
        name of the library
    _software_dir: str
        software path (ie build/target_name/software)
    _include_dir: str
        include directory path (ie build/target_name/software/include)
    _src_dir: str
        directory path where Makefile is located (litex/soc/software/XXX)
    """
    def __init__(self, libraryname, softwaredir, includedir, srcdir=None):
        """ CTOR

        Parameters
        ==========
        libraryname: str
            library name
        softwaredir: str
            software path
        includedir: str
            include directory path
        srcdir: str
            directory path where Makefile is located
        """
        self._library_name = libraryname
        self._software_dir = softwaredir
        self._include_dir  = includedir
        self._src_dir      = os.path.join(os.path.dirname(__file__), libraryname) if srcdir == None else srcdir

    def _create_dir(self, d, remove_if_exists=False):
        dir_path = os.path.realpath(d)
        if remove_if_exists and os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.makedirs(dir_path, exist_ok=True)

    def prepare_software(self):
        """ Creates directory where compilation output files must be located
        must be overloaded when more complex task must be done (git clone)
        """
        self._create_dir(os.path.join(self._software_dir, self._library_name)) 

    def build_software(self):
        """ builds software package (mainly uses subprocess to call make)
        """
        dst_dir  = os.path.join(self._software_dir, self._library_name)
        makefile = os.path.join(self._src_dir, "Makefile")
        subprocess.check_call(["make", "-C", dst_dir, "-f", makefile])

    @classmethod
    def get_library_inst(self, libraryname, softwaredir, includedir, srcdir=None):
        """ class method to return an instance of the `libraryname` library.
        May be None when not found, a PackageLibrary instance when no
        `library.py` is present or a specific object otherwise

        Parameters
        ==========
        libraryname: str
            library name
        softwaredir: str
            software path
        includedir: str
            include directory path
        srcdir: str
            directory path where Makefile is located

        Return
        ======
        an PackageLibrary, or subclass, object or None when not found
        """
        lib_cls = LIBRARIES.get(libraryname, None)
        if lib_cls is None:
            return None
        if lib_cls == PackageLibrary:
            lib_inst = PackageLibrary(libraryname, softwaredir, includedir, srcdir)
        else:
            lib_inst = lib_cls(softwaredir, includedir, srcdir)
        return lib_inst

    def __str__(self):
        """ return library name attribute when str is used

        Return
        ======
        Library name
        """
        return self._library_name

    @property
    def src_dir(self):
        """ return src_dir attribute
        
        Return
        ======
        src_dir attribute
        """
        return self._src_dir

    @property
    def lib(self):
        """ return library name
        
        Return
        ======
        library name
        """
        return "" if self._library_name == "bios" else self._library_name

# libraries Collection -----------------------------------------------------------------------------

def collect_libraries():
    """ collects libraries presents in sofware directory: loops on all
    directories and when a directory starts with 'lib' adds this one to the
    list. When the directory contains a 'library.py' try to adds corresponding
    class otherwise adds this library associated to the default PackageLibrary

    Return
    ======
    A dict where key is library name and content is the library class
    """
    libs  = {"bios": PackageLibrary}
    paths = [
        # Add litex.soc.software path.
        os.path.dirname(__file__),
        # Add execution path.
        os.getcwd()
    ]

    exec_dir = os.getcwd()

    # Search for libraries in paths.
    for path in paths:
        for file in os.listdir(path):

            # Verify that it's a path...
            lib_path = os.path.join(path, file)
            if not os.path.isdir(lib_path):
                continue

            # ... and that library.py is present.
            library = os.path.join(lib_path, "library.py")
            # no library: uses generic class
            if not os.path.exists(library):
                if file.startswith("lib"):
                    libs[file] = PackageLibrary
                continue # no library.py -> no more actions

            # library.py: get class and uses it instead of generic one
            lib = file
            sys.path.append(path)
            for lib_name, lib_cls in inspect.getmembers(importlib.import_module(lib), inspect.isclass):
                if lib_name.lower() in [lib, lib.replace("_", "")]:
                    libs[lib] = lib_cls

    # Return collected libraries.
    return libs

LIBRARIES = collect_libraries()
 

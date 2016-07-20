# -*- coding: utf-8 -*-
#
# pfpdb: Debugger for models built with the PFPSim Framework
#
# Copyright (C) 2016 Concordia Univ., Montreal
#     Samar Abdi
#     Umair Aftab
#     Gordon Bailey
#     Faras Dewal
#     Shafigh Parsazad
#     Eric Tremblay
#
# Copyright (C) 2016 Ericsson
#     Bochra Boughzala
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

'''
READ THIS YOU WILL REGRET IT OTHERWISE
Because Reasons:

Protobuf messages are used to communincate via IPC channel with the IPC Server
in a runnning simulation.

The python bindings for those messages is generated by the protoc compiler from
the .proto file.

This *_pb2.py file must be generated BEFORE setuptools install/develop command
is run.

To do that we inherit from setuptools install/develop classes for those
commands.
in the defintion of install.run(..) it checks the stack for the function
calle and if it is not setup( ) it does an old egg install from distutils
This is an active bug:

BUG: https://github.com/pypa/setuptools/issues/456

REF: https://github.com/pypa/setuptools/blob/
     29bef0ef4c71c0e9a88f1db889b47310568cc160
     /setuptools/command/install.py#L58

No we can't use distutils becuase we cant make a proper wheel out of it, thats
why they made setuptools in the first place.

So whats the fix ?

For
python setup.py install
python setup.py develop

In the superclassed commands we run pip explicility with the install_requires

ADD YOUR REQUIREMENT TO THE InstallationRequirments LIST PIP WILL INSTALL
THOSE PACKAGES ONE BY ONE IN THAT LIST.
'''

"""setup.py: setuptools control."""

import re
import subprocess
import os
import sys

# Find setuptools
try:
  from setuptools import setup, Extension
  from setuptools import find_packages
  from setuptools.command.install import install
  from setuptools.command.develop import develop
  from setuptools.command.sdist import sdist
except ImportError:
  try:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, Extension, find_packages
    from setuptools.command.install import install
    from setuptools.command.develop import develop
    from setuptools.command.sdist import sdist
  except ImportError:
    sys.stderr.write(
        "Could not import setuptools; make sure you have setuptools or "
        "ez_setup installed\n")
    raise

from distutils.command.clean import clean as _clean
from distutils.command.build_py import build_py as _build_py
from distutils.spawn import find_executable
try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    import distutils.cmd
    class bdist_wheel(distutils.cmd.Command):
        def finalize_options(self):
            pass
        def initialize_options(self):
            pass
        user_options = []
        def run(self):
            sys.stderr.write(
                "wheel.bdist_wheel NOT FOUND "
                "please run: pip install wheel\n")
            sys.exit(-1)

InstallationRequirments = [
    'nnpy',
    'tabulate',
    'hexdump',
    'colour',
    'matplotlib'
]

if sys.version_info[0] < 3:
    InstallationRequirments.append("protobuf")
else:
    InstallationRequirments.append("protobuf==3.0.0b2")

# Find the Protocol Compiler.
if 'PROTOC' in os.environ and os.path.exists(os.environ['PROTOC']):
  protoc = os.environ['PROTOC']
elif os.path.exists("../src/protoc"):
  protoc = "../src/protoc"
elif os.path.exists("../src/protoc.exe"):
  protoc = "../src/protoc.exe"
elif os.path.exists("../vsprojects/Debug/protoc.exe"):
  protoc = "../vsprojects/Debug/protoc.exe"
elif os.path.exists("../vsprojects/Release/protoc.exe"):
  protoc = "../vsprojects/Release/protoc.exe"
else:
  protoc = find_executable("protoc")

#http://stackoverflow.com/questions/27843481/python-project-using-protocol-buffers-deployment-issues
def generate_proto(source):
    """Invokes the Protocol Compiler to generate a _pb2.py from the given
    .proto file.  Does nothing if the output already exists and is newer than
    the input."""
    # Find the Protocol Compiler.
    output = source.replace(".proto", "_pb2.py")

    if (not os.path.exists(output) or
        (os.path.exists(source) and os.path.getmtime(source) > os.path.getmtime(output))):
        print ("Generating %s..." % output)
        if not os.path.exists(source):
            sys.stderr.write("Can't find required file: %s\n" % source)
            sys.exit(-1)
        #protoc="protoc"
        if protoc == None:
            sys.stderr.write(
                "protoc is not installed nor found in ../src.  Please compile it "
                "or install the binary package.\n")
            sys.exit(-1)

        protoc_command = [ protoc, "-I=./pfpdb/", "--python_out=./pfpdb/", source ]

        if subprocess.call(protoc_command) != 0:
            sys.stderr.write("Could Not generate Proto bindings for python - Please ensure protobuf compiler is installed and working")
            sys.exit(-1)

def installfrompip(packagestoinstall):
    if isinstance(packagestoinstall,list):
        print ("Installing Dependencies")
        for package in packagestoinstall:
            print ("Installing "+str(package))
            subprocess.call(["pip","install",str(package)])
        print ("Done Installing")
    else:
        sys.stderr.write(
            "Can't install from pip - passed requirments is"
            "not a list.\n")
        sys.exit(-1)

class pfpdbinstall(install):

    def run(self):
        installfrompip(InstallationRequirments);
        #subprocess.call(["protoc", "-I=./pfpdb/",  "--python_out=./pfpdb/", "./pfpdb/PFPSimDebugger.proto"])
        generate_proto("./pfpdb/PFPSimDebugger.proto")
        install.run(self)

class pfpdbdevelop(develop):

    def run(self):
        installfrompip(InstallationRequirments);
        #subprocess.call(["protoc", "-I=./pfpdb/",  "--python_out=./pfpdb/", "./pfpdb/PFPSimDebugger.proto"])
        generate_proto("./pfpdb/PFPSimDebugger.proto")
        develop.run(self)

class clean(_clean):
  def run(self):
    # Delete generated files in the code tree.
    for (dirpath, dirnames, filenames) in os.walk("."):
      for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        if filepath.endswith("_pb2.py"):
          os.remove(filepath)
    # _clean is an old-style class, so super() doesn't work.
    _clean.run(self)

class _bdist_wheel(bdist_wheel):
    def run(self):
        generate_proto("./pfpdb/PFPSimDebugger.proto")
        bdist_wheel.run(self)

version = re.search(
    '^__version__\s*=\s*"(.*)"',
    open('pfpdb/pfpdb.py').read(),
    re.M
    ).group(1)


with open("README.md", "rb") as f:
    long_descr = f.read().decode("utf-8")


setup(
    name = "pfpdb",
    packages = find_packages(),
    entry_points = {
        "console_scripts": ['pfpdb = pfpdb.pfpdb:main']
        },
    version = version,
    description = "PFPSIM Debugger",
    long_description = long_descr,
    author = "Samar Abdi",
    author_email = "pfpsim.help@gmail.com",
    keywords = "PFPGEN FAD SDN NPU P4 Dataplane 5G System Debugger",
    url = "pfpsim.github.io",
    install_requires=InstallationRequirments,
    cmdclass={
        'install':pfpdbinstall,
        'develop':pfpdbdevelop,
        'clean':clean,
	'bdist_wheel':_bdist_wheel
        },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Natural Language :: English",
        "Operating System :: Unix",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Debuggers",
    ],
    )

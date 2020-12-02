# MAERI 0.1

[Not yet ready!]

An end to end implementation of an ML CNN accelerator.

 - Go from Tensorflow down to FPGA.
 - You can stream in an image to be classified over 
ethernet to the FPGA as many times as you want
without reconfiguring.
 - 100% FOSS. Even the FPGA PNR and Synth tools
(which were reverse engineered).
 - RTL extensively **formally** verified.

# Overview
Below is a high level overview of the hardware.

![High level overview](docs/high_level.svg)

# Dependencies

 - [yosys](https://github.com/YosysHQ/yosys)
 - [symbiyosys](https://symbiyosys.readthedocs.io/en/latest/quickstart.html#symbiyosys)
 - [yices2](https://github.com/SRI-CSL/yices2)

 Yosys and yices2 can both be installed with [homebrew](https://brew.sh)
 (Mac) or [linuxbrew](https://docs.brew.sh/Homebrew-on-Linux)

 ```bash
brew install bracketmaster/rtl/yosys
brew install SRI-CSL/sri-csl/yices2
```

## Caveats
On MacOS BigSur, you might have install numpy manually:
```bash
brew install openblas
OPENBLAS="$(brew --prefix openblas)" pip3 install numpy
```

# Installing

You should probably use a virtual environment.
Change to wherever you install your virtual environments.

```bash
pip3 install virtualenv
mkdir -p ~/.virtualenvs
cd ~/.virtualenvs
python3 -m venv maeri
source ~/.virtualenvs/maeri_v6/bin/activate
git clone https://github.com/BracketMaster/maeri
cd maeri
pip3 install -e .
```

# Getting Started

First connect the ULX3s to the host using the USB1
port on the ULX3s.

You can program the ULX3s with the accelerator by doing:

```bash
cd maeri/gateware/platform/ulx3s
python3 top.py
openFPGALoader -f -b ulx3s build/top.bit 
```

Now connect the ULX3s to the host using the USB2
port on the ULX3s.

You can test the driver from the ULX3s with:

```bash
cd test
PLATFORM=ulx3s python3 test_driver.py
```

You can test the assembler together with the 
accelerator with:
```
cd maeri/gateware/compute_unit
python3 test_top.py
```

You can test the compiler with:

```
cd maeri/compiler/tests
python3 test_compiler.py
```

# Running Tests

To run all the unit tests in succession,
do including formal tests:

```
python -m unittest discover -s test -v
```

Typically, the simulator state is preserved 
between unit tests to avoid having to setup
and tear down the simulator between each 
unit test.

## Running Formal Tests

To run a specific formal unit test(or really
any unit test), do something to the effect
of:

```
python3 test/gateware/test_adder_node.py
```

# Status

Need to update this...

# LOC Count
Keep forgetting how to do this.

```bash
find . -type f -name "*.py" | xargs wc -l
```

# Optimizations

 - faster configurations
   - I should be able to easily do this with mem-width
   of four and four config ports.
   I remove the extra top config port that is/was
   introduced? Was it actually introduced?
#!/bin/bash
yosys -p 'synth_ecp5 -json top.json -abc9' maeri_hw.v
nextpnr-ecp5 --json top.json --um-85k --textcfg top_out.config
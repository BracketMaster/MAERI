# Gateware
 - [ ] compute domain should remain "compute" and be
changed in the final lowering state
I should be able to go ahead and give compute its own PLL
 - [ ] mem and compute need to be in the same domain
 - [ ] state machine for the compute unit can connect
 directly to the memory
   - [ ] need to generate PLL for this
   - [ ] pll1 and pll2

# Gateware Tests
 - [ ] Add some infrastructure to run the reduction tests
 - [ ] add asserts for nodes who's outputs should be zero
in the network reduction tests
 - [ ] test integration on Github

# Misc
 - [ ] add README with basic diagrams
 - [ ] add tests manually to script
 - [ ] remove `customize` and merge to platform
 - [ ] automatic support for webasm yosys and nextpnr
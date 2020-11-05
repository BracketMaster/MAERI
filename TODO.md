# Gateware Tests
 - [ ] Add some infrastructure to run the reduction tests
 - [ ] add asserts for nodes who's outputs should be zero
in the network reduction tests
 - [ ] test integration on Github

# High Level Plan
 - need a binary packer and binary reader
 - will be called compute core
 - compute core makes memory load/store requests
 and updates it's status

# Adding Support for Config
 - state machine with access to memory
   - set states
   - set weights
 - drivers
   - create ISA file structure
   - create hardware
   - iterate and converge

# Misc
 - [ ] remove tinyFPGA as a platform
 - [ ] add README with basic diagrams
 - [ ] add tests manually to script
 - [ ] remove `customize` and merge to platform
 - [ ] automatic support for webasm yosys and nextpnr

# Make a Formal Integration for the test Vectors
test_settings = [28, 2, 5, 8, 2, 16, 16]
test_settings = [28, 1, 5, 8, 2, 16, 16]
test_settings = [4, 2, 3, 2, 2, 16, 16]
test_settings = [4, 2, 3, 2, 1, 16, 16]
test_settings = [4, 2, 3, 4, 1, 16, 16]
test_settings = [4, 2, 3, 4, 2, 16, 16]
test_settings = [4, 2, 4, 4, 3, 16, 16]

# Optimizations
 - remove en from the write and read port
 - might make sense to put compute into a
faster domain later
   - you might need a cache to make this
benefitial

# Nov 6
 - maeri base controller
   - need memory adaptor
 - hdf5 h5py
   - I need a way to delineate commands in the
binary
   - write, read, start, status
 - i need a status afifo
 - i need a start afifo
 - setup GitHub CI

 - CocoTB integration needed for speedup

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

# MAERI core
 - must be able to command the core to start
 - must be able to see whether or not the core
 is busy

# Adding Support for Config
 - state machine with access to memory
   - set states
   - set weights
 - drivers
   - create ISA file structure
   - create hardware
   - iterate and converge

# Misc
 - rename top level common to shared
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
beneficial
- better space utilization for opcodes
   - involves making an interface adaptor
   which we need anyways

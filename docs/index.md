# Welcome to MAERI on FPGA Version 6

Full documentation available [here](https://bracketmaster.github.io/MAERI-RTL/).
Paper on which this project is based [here](https://dl.acm.org/doi/pdf/10.1145/3296957.3173176)

MAERI is a flexible hardware architecture for accelerating a certain class of machine learning workloads. This project aims to provide an easy to access reference codebase for a MAERI implmentation.

In addition, this project aims to provide a flexible end to end solution for a discrete implmentation of MAERI, such as MAERI inside an FPGA connected to a host machine over PCIE or Ethernet.

The end result of this particular project will be MAERI implmented on an FPGA connected to a host machine over PCIE running trained MNIST layers.

There is a seperate host-side ML workload compiler called MRNA that will soon be able to target MAERI directly. More on this later...
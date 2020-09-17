import os
from termcolor import colored
max_packet_size = 32

try:
    if os.environ['PLATFORM'] == None:
        raise ValueError()
    if (os.environ['PLATFORM'] not in {'tinyfpga', 'sim'}):
        print(colored(f"INVALID OPTION!: PLATFORM={os.environ['PLATFORM']}", 'red'))
        raise ValueError()
    else:
        platform = os.environ['PLATFORM']
except:
    platform = 'sim'
    print(colored("RUNNING on nMigen Simulation Model",'blue'))
    print(colored("CHANGE WITH PLATFORM=tinyfpga or PLATFORM=sim",'blue'))
    print()

if platform == 'sim':
    try:
        if os.environ['ENGINE'] == None:
            raise ValueError()
        if (os.environ['ENGINE'] not in {'cxxsim', 'pysim'}):
            print(colored(f"INVALID OPTION!: ENGINE={os.environ['ENGINE']}", 'red'))
            raise ValueError()
        else:
            engine = os.environ['ENGINE']
    except:
        engine = 'pysim'
        print(colored("DEFAULTING TO PYSIM",'blue'))
        print(colored("CHANGE WITH ENGINE=pysim or ENGINE=cxxsim",'blue'))
        print()

if platform == 'sim':
    try:
        if os.environ['VCD'] == None:
            raise ValueError()
        if (os.environ['VCD'] not in {'on', 'off'}):
            print(colored(f"INVALID OPTION!: VCD={os.environ['VCD']}", 'red'))
            raise ValueError()
        else:
            vcd = os.environ['VCD']
    except:
        vcd = 'on'
        print(colored(f"VCD WRITE: {vcd}",'blue'))
        print(colored("CHANGE WITH VCD=on or VCD=off",'blue'))
        print()
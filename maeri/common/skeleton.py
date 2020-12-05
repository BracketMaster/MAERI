"""
Provides tree structure for the reduction network.

Instances of nmigen adders and mults are later
instantiated and connected referencing the 
connections represented in the lists created 
when ``Skeleton`` is called.

The compiler will also reference an instance
of ``Skeleton`` to help it make valid transformation
decisions for the particular configuration
of MAERI hardware it's targetting.

Builds MAERI binary tree.
Example:
    $ python3 src/substrate/skeleton.py
    ADDER NODE ID:0
    ADDER NODE ID:1
    ADDER NODE ID:2

    MULT NODE ID:3
    MULT NODE ID:4
    MULT NODE ID:5
    MULT NODE ID:6


    MULT FORWARDING LINK (3,4)
    MULT FORWARDING LINK (4,5)
    MULT FORWARDING LINK (5,6)

    CONFIG GROUP 0 NODES: [1, 3, 4]
    CONFIG GROUP 1 NODES: [2, 5, 6]
    CONFIG GROUP 2 NODES: [0]

    NODE 6 HAS INJECTION PORT
    NODE 4 HAS INJECTION PORT
"""

from maeri.common.node import Node
from math import log2, floor
from functools import reduce

class Skeleton():
    def __init__(self,depth, num_ports, bytes_in_line, VERBOSE=False):
        """
        Attributes:
        ===========
        self.all_nodes:
            list containing all the nodes objects in the balanced 
            binary tree
        self.adder_nodes:
            list containing only adder node objects
        self.mult_nodes:
            list containing only mult node objects
        self.inject_nodes:
            list containing node objects which have injection ports
        self.config_groups:
            list of sub-lists. `index` in `self.config[index]`
            corresponds to a conifgure port.
            All the nodes in a particular sublist can be configured
            by the corresponding configure port.
        self.mult_forwarding_links:
            list of two-element tuples representing pairs of
            multipliers that share a forwarding link
        self.adder_forwarding_links:
            list of two-element tuples representing pairs of
            adders that share a forwarding link
        """
        try:
            self.depth = depth

            if((depth < 2) or (depth > 8)):
                raise ValueError(
                    f"depth = {depth} invalid. " + 
                    "MAERI only supports depths on domain [2,8] " +
                    "inclusive at this time."
                    )

            # root Node of tree starts at index 1
            self.__tree = [None]
            tree = self.__tree

            # add nodes to tree list
            for i in range(1,2 ** depth):
                tree.append(Node(
                    id=i,
                    latency=(depth - floor(log2(i)))
                    ))
            
            # partition node types
            self.all_nodes = tree[1:]
            self.adder_nodes = tree[1:(2 ** (depth - 1))]
            self.mult_nodes = tree[(2** (depth - 1)):]

            # alias for easy access
            all_nodes = self.all_nodes
            adder_nodes = self.adder_nodes
            mult_nodes = self.mult_nodes

            # add edges to tree
            for i in range(1,2**(depth-1)):
                tree[i*2].parent = tree[i]
                tree[(i*2)+1].parent = tree[i]
                tree[i].lhs = tree[i * 2]
                tree[i].rhs = tree[(i * 2)+1]

            # list of forwarding links for adder
            self.adder_forwarding_links = []
            for (node1, node2) in zip(adder_nodes[2::2], adder_nodes[3::2]):

                # is node1 or node2 an edge Node?
                if (log2(node1.id + 1) % 1) == 0:
                    continue

                if (log2(node2.id) % 1) == 0:
                    continue

                self.adder_forwarding_links.append((node1, node2))
            
            # nodes each memory port can config
            self.config_groups = []
            for index in range(bytes_in_line):
                self.config_groups += [all_nodes[index::bytes_in_line]]

            #print(self.config_groups)

            # list of forwarding links for mults
            self.mult_forwarding_links = []
            for (node1, node2) in zip(mult_nodes[0:], mult_nodes[1:]):
                self.mult_forwarding_links.append((node1, node2))

            # validate that there is a valid number
            # of injection ports 
            if (log2(num_ports) % 1 != 0):
                raise ValueError("argument: num_ports must be "+
                                "a power of two")
            if (num_ports <= 0):
                raise ValueError("argument: num_ports must be "+
                                "greater than 0")
            if (num_ports > 2**(depth - 2)):
                raise ValueError(f"for DEPTH={self.depth}, "
                                "argument num_ports must "+
                                f"be less than or equal to"+
                                f" {2**(depth - 2)}")
            
            # nodes to which injection ports shall
            # be connected
            leftmost_leaf = 2**(depth - 1) - 1
            rightmost_leaf = 2**(depth) - 1
            interval = int((2**(depth - 1))/num_ports)
            selection = slice(rightmost_leaf, leftmost_leaf, -interval)
            self.inject_nodes = self.all_nodes[selection]
            self.inject_nodes.reverse()

            # make nodes zero adressable in hardware
            # It is impossible to address node 128 with 8 bits,
            # so we must make node 128 become node 127 and 
            # node 1 becomes node 0

            # must shift node IDs from [1, 2**depth] to
            # [0, (2**depth) - 1]
            for node in all_nodes:
                node.id -= 1
            
            if VERBOSE:
                self.debug()
        except:
            raise Exception(
                'UNABLE to GENERATE REQUESTED REDUCTION NETWORK\n' + 
                f'OF DEPTH={self.depth}, PORTS={num_ports}')


    def get_children(self, root):
        if root:
            yield root
            yield from self.get_children(root.lhs)
            yield from self.get_children(root.rhs)
    
    def debug(self):
        print("INSTANTIATING SKELETON\n")

        print()
        for node in self.adder_nodes:
            print(f"ADDER NODE: ID {node.id} : LATENCY {node.latency}")

        print()
        for node in self.mult_nodes:
            print(f"MULT NODE: ID {node.id} : LATENCY {node.latency}")

        print()
        for node1, node2 in self.adder_forwarding_links:
            print(f"ADDER FORWARDING LINK ({node1.id},{node2.id})")

        print()
        for node1, node2 in self.mult_forwarding_links:
            print(f"MULT FORWARDING LINK ({node1.id},{node2.id})")

        print()
        for node in self.inject_nodes:
            print(f"NODE {node.id} HAS INJECTION PORT")
        
        print()
        for index, group in enumerate(self.config_groups):
            print(f"group_{index}  = {[node.id for node in group]}")


if __name__ == "__main__":
    from sys import argv
    Skeleton(4, 4, VERBOSE=1)
    #Skeleton(int(argv[1]), int(argv[2]), VERBOSE=1)

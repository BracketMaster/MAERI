from maeri.common.logger import LogIndent, logger
from maeri.compiler.sanitize.sanitize import sanitize
from maeri.compiler.build_graph import build_memories
from maeri.compiler.schedule import schedule
from maeri.compiler.build_graph import build_conv
from maeri.compiler.build_graph import build_root
from maeri.compiler.build_graph import build_result

from maeri.compiler.nodes.Conv2 import Conv2
from maeri.compiler.nodes.Add import Add

from maeri.compiler.solver import solve_conv
from maeri.compiler.solver import solve_add

import numpy as np

import onnx

class Compile():
    def __init__(self, model_path, buff_length=128, ports=4):
        self.buff_length = buff_length
        self.ports = ports
        model = onnx.load(model_path)
        model = sanitize(model)
        #onnx.save(model, f"{model_path[:-5]}-sanitized.onnx")

        ordered_nodes = schedule(model)
        # TODO : remove name_v_mem from self
        name_v_mem = build_memories(model)
        self.memories = memories = list(name_v_mem.values())

        self.op_graph = op_graph = []
        self.entrypoint = build_root(model, name_v_mem)
        self.exitpoint = build_result(model, name_v_mem)

        for node in ordered_nodes:
            if node.op_type == "Conv":
                logger.debug(f"Compiling Convolutional Node: {node.name}")

                with LogIndent():
                    ops_, mems_ = build_conv(node, name_v_mem)
                    op_graph += ops_
                    memories += mems_
                
                break
    
    def sim(self, data):
        logger.debug("RUNNING SIMULATION")
        with LogIndent():
            self.entrypoint.init_root(data)
            [op.sim() for op in self.op_graph]
            return self.exitpoint.get_data()
    
    def solve(self):
        logger.debug("SOLVING GRAPH")
        op_graph = self.op_graph
        op_graph_new = []

        with LogIndent():
            for op in op_graph:

                # Solve Conv2 nodes
                if type(op) is Conv2:
                    op_graph_new += solve_conv(op, self.buff_length, self.ports)
                elif type(op) is Add:
                    op_graph_new += solve_add(op, self.buff_length, self.ports)
                else:
                    # TODO : should be raising error
                    op_graph_new += [op]
        print(f"Original op count : {len(op_graph)}")
        print(f"Final op count : {len(op_graph_new)}")
        self.op_graph = op_graph_new
    
    def bake_offsets(self):
        # first, build the zero node
        zeros = np.zeros([self.ports, self.buff_length])

        # the zeros memory is always the first node
        # on the memory list
        self.memories.insert(0, zeros)

        offset = len(self.memories[0].data.flatten())
        self.memories[0].offset = 0
        for memory in self.memories:
            memory.offset = offset
            offset = len(memory.data.flatten())
    
    def debug(self):
        op_graph = self.op_graph

        for op in op_graph:
            if type(op) is Conv2:
                logger.debug("DEBUGGING CONV NODE")
                with LogIndent():
                    op.debug()
from maeri.common.logger import logger, LogIndent
from maeri.compiler.nodes import Memory

import numpy as np

def build_memories(model):

    name_v_mem = {}

    input_names = [_.name for _ in model.graph.input]
    output_names = [_.name for _ in model.graph.output]
    valueinfo_names = [_.name for _ in model.graph.value_info]

    logger.debug("Adding memory for model.graph.input")
    with LogIndent():
        for input_ in model.graph.input:
            dims = [dim.dim_value for dim in input_.type.tensor_type.shape.dim]
            data = np.zeros(dims)

            # add memory node to lists
            name_v_mem[input_.name] = Memory(data)
            logger.debug(f"Creating memory for {input_.name}")

    logger.debug("Adding memory for model.graph.value_info")
    with LogIndent():
        for input_ in model.graph.value_info:
            dims = [dim.dim_value for dim in input_.type.tensor_type.shape.dim]
            data = np.zeros(dims)

            # add memory node to lists
            name_v_mem[input_.name] = Memory(data)
            if input_.name in input_names:
                logger.debug(f"Replacing memory for {input_.name}")
            else:
                logger.debug(f"Creating memory for {input_.name}")

    logger.debug("Adding memory for model.graph.output")
    with LogIndent():
        for input_ in model.graph.output:
            dims = [dim.dim_value for dim in input_.type.tensor_type.shape.dim]
            data = np.zeros(dims)

            # add memory node to lists
            name_v_mem[input_.name] = Memory(data)
            if input_.name in input_names + valueinfo_names:
                logger.debug(f"Replacing memory for {input_.name}")
            else:
                logger.debug(f"Creating memory for {input_.name}")

    logger.debug("Adding memory for model.graph.initializer")
    with LogIndent():
        for input_ in model.graph.initializer:
            dims = input_.dims

            # get data for memory instance
            if input_.float_data:
                data = np.array(input_.float_data).reshape(dims)
            else:
                logger.debug(f"{input_.name} has no data")
                data = np.zeros(dims)
            
            # add memory node to lists
            name_v_mem[input_.name] = Memory(data)
            if input_.name in input_names + valueinfo_names + output_names:
                logger.debug(f"Replacing memory for {input_.name}")
            else:
                logger.debug(f"Creating memory for {input_.name}")
    
    return name_v_mem

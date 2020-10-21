from maeri.common.logger import logger, LogIndent
from maeri.compiler.nodes import Memory, Input, Output
from maeri.compiler.nodes import Conv2, Add

import numpy as np

def get_pads(conv_node):
    pads = []
    for attribute in conv_node.attribute:
        if attribute.name == 'pads':
            pads = attribute.ints
    
    return pads

def build_conv(conv_node, name_v_mem):
    INPUT = conv_node.input[0]
    FILTER = conv_node.input[1]
    OUTPUT = conv_node.output[0]
    if len(conv_node.input) == 3:
        BIAS = conv_node.input[2]
        raise NotImplementedError("Compiler does not yet support bias.")

    input_mem = name_v_mem[INPUT]
    filter_mem = name_v_mem[FILTER]
    output_mem = name_v_mem[OUTPUT]

    input_dims = input_mem.data.shape
    filter_dims = filter_mem.data.shape
    output_dims = output_mem.data.shape

    # SANITY CHECK : For matching dimensions on inputs
    # and outputs
    assert(output_dims[1] == filter_dims[0])

    # Compiler currently unable to reason about conv
    # inputs that are not 4d
    assert(len(input_dims) == 4)
    assert(len(filter_dims) == 4)

    # Compiler unable to reason about non-square inputs
    # or filters
    assert(input_dims[2] == input_dims[3])
    assert(filter_dims[2] == filter_dims[3])

    # I don't even know how to perform a convolution on
    # on inputs having a 4th dimension with a depth
    # greater than 1
    # NOTE : 0 indexes into the 4th dimension below 
    # due to onnx's reversed indexing
    assert(input_dims[0] == 1)

    pads = get_pads(conv_node)
    assert(len(pads) == 4)

    # currently only supporting uniform padding
    assert(pads[0] == pads[1] == pads[2] == pads[3])
    pad = pads[0]

    # compiler currently unable to support more padding
    # than the filter depth
    assert(pad < filter_dims[2])

    ops = []
    mems = []

    # build convolutional graph
    f_size_slice = slice(0, filter_dims[2])
    i_size_slice = slice(0, input_dims[2])
    o_size_slice = slice(0, output_dims[2])

    # if there is only one channel
    if filter_dims[1] == 1:
        for output in range(filter_dims[0]):
            input_slice = (0, 0, i_size_slice, i_size_slice)
            X = Input(input_slice, input_mem)

            filter_slice = (output, 0, f_size_slice, f_size_slice)
            W = Input(filter_slice, filter_mem)

            output_slice = (0, output, o_size_slice, o_size_slice)
            res = Output(output_slice, output_mem)

            ops += [Conv2(X, W, res, [pad]*4)]
    
    # if there is more than one channel
    elif filter_dims[1] > 1:
        # TODO, return buffer
        buffer_mem = Memory(np.zeros([1,1,output_dims[2],output_dims[2]]))
        mems += [buffer_mem]
        buffer_slice = (0, 0, o_size_slice, o_size_slice)

        for output in range(filter_dims[0]):
            for channel in range(filter_dims[1]):
                input_slice = (0, channel, i_size_slice, i_size_slice)
                X = Input(input_slice, input_mem)

                filter_slice = (output, channel, f_size_slice, f_size_slice)
                W = Input(filter_slice, filter_mem)

                output_slice = (0, output, o_size_slice, o_size_slice)

                if channel == 0:
                    res = Output(output_slice, output_mem)
                    ops += [Conv2(X, W, res, [pad]*4)]

                else:
                    buf_res = Output(buffer_slice, buffer_mem)
                    
                    a = Input(output_slice, output_mem)
                    b = Input(buffer_slice, buffer_mem)
                    c = Output(output_slice, output_mem)
                    ops += [Conv2(X, W, buf_res, [pad]*4), Add(a, b, c)]

    else:
        raise ValueError(f"filter_dims[1] of {filter_dims[1]} is less than 1.")

    return ops, mems

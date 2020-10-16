from maeri.compiler.sanitize.extended_model import ExtendedModel
from maeri.common.logger import logger, LogIndent

from maeri.compiler.sanitize.conv_pad_pass import explicit_pad_pass
from maeri.compiler.sanitize.conv_valid_pass import conv_valid_pass

import onnx
import onnx.utils
from onnx import optimizer

def sanitize(model):
    # compiler currently unable to reason about
    # batch normalization, fusing helps
    passes = ['fuse_bn_into_conv', 'fuse_pad_into_conv']
    model = optimizer.optimize(model, passes)
    model = onnx.utils.polish_model(model)

    # some validity checks
    if len(model.graph.sparse_initializer) != 0:
        raise NotImplementedError("Does not yet support sparse inits.")
    if len(model.graph.output) != 1:
        raise NotImplementedError("Currently only supports single output models.")

    with ExtendedModel(model) as extended_model:
        for node in extended_model.graph.node:
            logger.debug(f"Operating on node {node.name}")
            with LogIndent():
                if node.op_type == 'Conv':
                    conv_valid_pass(node, extended_model)
                    explicit_pad_pass(node, extended_model)
                else:
                    logger.debug("No passes applied.")

    return model

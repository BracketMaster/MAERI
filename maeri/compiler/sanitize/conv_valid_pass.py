import onnx
from onnx.helper import make_attribute

from maeri.compiler.sanitize.lookup_ref import lookup_ref_dims_by_name
from maeri.common.logger import logger

def conv_valid_pass(node, extended_model):
    """
    Check that current node has only attributes that can
    be successfully lowered by our compiler.
    """
    ordered_attributes = []
    ordered_names = []
    for attribute in node.attribute:
        ordered_names += [attribute.name]
        ordered_attributes += [attribute]

    # check that node has auto_pad attribute
    dilation_attribute = None
    for index, name in enumerate(ordered_names):
        if name == 'dilations':
            dilation_attribute = ordered_attributes[index]
            break
    
    if not dilation_attribute:
        logger.warn("Dilation not specified")
        logger.warn("Assuming dilation of [1,1].")
        return
    
    if dilation_attribute.ints != [1,1]:
        raise NotImplementedError("Currently only supporting " +\
            f"dilations of size [1,1] not {dilation_attribute.ints}")

    logger.debug(f"FINISHED {conv_valid_pass.__name__} pass")
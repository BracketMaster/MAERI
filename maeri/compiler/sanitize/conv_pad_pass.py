import onnx
from onnx.helper import make_attribute

from maeri.compiler.sanitize.lookup_ref import lookup_ref_dims_by_name
from maeri.common.logger import logger

def explicit_pad_pass(node, extended_model):
    """
    Transform implicit pads into explicit pads.
    """

    ordered_attributes = []
    ordered_names = []
    for attribute in node.attribute:
        ordered_names += [attribute.name]
        ordered_attributes += [attribute]

    # check that node has auto_pad attribute
    auto_pad_attribute = None
    for index, name in enumerate(ordered_names):
        if name == 'auto_pad':
            auto_pad_attribute = ordered_attributes[index]
            break
    
    if not auto_pad_attribute:
        logger.debug("SKIPPING auto_pad pass")
        return
    
    auto_pad = auto_pad_attribute.s.decode("utf-8")
    if auto_pad != "SAME_UPPER":
        raise NotImplementedError(f"Only `SAME_UPPER` autopad currently" +  \
            f" supported, not {auto_pad}.")
    
    dims = lookup_ref_dims_by_name(node.input[1], extended_model)[-2:]

    if dims[0] != dims[1]:
        raise NotImplementedError("Currently only supporting square filters.")

    # TODO : check  if padding even
    
    pad_length = int((dims[0] - 1)/2)
    node.attribute.remove(auto_pad_attribute)
    node.attribute.append(make_attribute('pads', [pad_length]*4))
    logger.debug(f"FINISHED {explicit_pad_pass.__name__} pass")
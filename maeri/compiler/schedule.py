from maeri.common.logger import LogIndent, logger
import onnx

def schedule(model):
    schedule = []
    collected_outputs = []

    collected_inputs = [_.name for _ in model.graph.input]
    collected_inputs += [_.name for _ in model.graph.initializer]
    collected_inputs = list(set(collected_inputs))

    logger.debug("NOW SCHEDULING")

    with LogIndent():
        while len(model.graph.node) > 0:
            for node in model.graph.node:
                combined_references = collected_inputs + collected_outputs
                inputs_satisfied = all([input_ in combined_references for input_ in node.input])
                if inputs_satisfied:
                    model.graph.node.remove(node)
                    collected_outputs += list(node.output)
                    schedule += [node]
                    logger.debug(node.name)
                    break
    
    return schedule
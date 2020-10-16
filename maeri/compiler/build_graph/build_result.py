from maeri.compiler.nodes import Result

def build_result(model, name_v_mem):
    mem_ref = name_v_mem[model.graph.output[0].name]
    slice_ = tuple([slice(len) for len in mem_ref.data.shape])
    return Result(slice_, mem_ref)

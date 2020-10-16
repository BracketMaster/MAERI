from maeri.compiler.nodes import Root

def build_root(model, name_v_mem):

    # finds the root/input for the model
    input_names = [_.name for _ in model.graph.input]
    init_names = [_.name for _ in model.graph.initializer]
    vinfo_names = [_.name for _ in model.graph.value_info]

    for name in input_names:
        if name not in init_names:
            if name not in vinfo_names:
                break

    mem_ref = name_v_mem[name]
    slice_ = tuple([slice(len) for len in mem_ref.data.shape])
    return Root(slice_, mem_ref)

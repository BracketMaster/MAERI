import onnx

def lookup_ref_dims_by_name(ref, extended_model):
    output_by_name = extended_model.output_by_name
    value_by_name = extended_model.value_by_name
    input_by_name = extended_model.input_by_name
    init_by_name = extended_model.init_by_name

    if ref in output_by_name.keys():
        ref = output_by_name[ref]
        return [_.dim_value for _ in ref.type.tensor_type.shape.dim]

    if ref in value_by_name.keys():
        ref = value_by_name[ref]
        return [_.dim_value for _ in ref.type.tensor_type.shape.dim]

    if ref in input_by_name.keys():
        ref = input_by_name[ref]
        return [_.dim_value for _ in ref.type.tensor_type.shape.dim]

    if ref in init_by_name.keys():
        ref = init_by_name[ref]
        return ref.dims

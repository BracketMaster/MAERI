from onnx.helper import make_node
import numpy as np

# test dimensions
input_shape = 9
channels = 1
kernel_width = 3
no_kernels = 1
padding = 0
buff_length = 5

# randomly generate test vectors
from random import randint
x_shape = (1,channels,input_shape,input_shape)
x_data = [randint(0,4) for num in range(np.prod(x_shape))]
W_shape = (no_kernels,channels,kernel_width,kernel_width)
W_data = [randint(0,4) for num in range(np.prod(W_shape))]

x = np.array(x_data).reshape(x_shape).astype(np.float32)
W = np.array(W_data).reshape(W_shape).astype(np.float32)

# Convolution with padding
node_with_padding = make_node(
    'Conv',
    inputs=['x', 'W'],
    outputs=['y'],
    kernel_shape= [kernel_width]*2,
    # Default values for other attributes: 
    # strides=[1, 1], dilations=[1, 1], groups=1
    strides=[1, 1],
    pads= [padding]*4
    )

import onnx
from onnx.helper import make_tensor_value_info
from onnx.helper import make_tensor, make_graph
from onnx.helper import make_tensor, make_model
from onnx import AttributeProto, TensorProto, GraphProto

# compute shape of output y
out_inner_dims = (x.shape[2] + 2*padding) - W.shape[2] + 1
# out_inner_dims = x.shape[2] - W.shape[2] + 1
y_shape = [1, W.shape[0], out_inner_dims, out_inner_dims]


x_input = make_tensor_value_info('x', TensorProto.FLOAT, list(x.shape))
W_input = make_tensor_value_info('W', TensorProto.FLOAT, list(W.shape))
y_output = make_tensor_value_info('y', TensorProto.FLOAT, y_shape)

W_init = make_tensor('W', TensorProto.FLOAT, list(W.shape), W.flatten())

graph = make_graph(
        nodes=[node_with_padding],
        name='test1',
        inputs=[x_input, W_input],
        initializer=[W_init],
        outputs=[y_output])

# write model to file
model_def = make_model(graph, producer_name='onnx-example')
onnx.checker.check_model(model_def)
onnx.save(model_def, 'test.onnx')

# run model with onnx runtime
import onnxruntime as rt
sess = rt.InferenceSession('test.onnx')
res = sess.run(['y'], {'x':x})

# compile model and run with compiler's
# executor
from maeri.compiler.compile import Compile
import numpy as np
sess = Compile("test.onnx", buff_length=buff_length)
res_1 = sess.sim(x)

# check that the results are the same
assert((res - res_1).sum() == 0)

# now solve the graph for hardware
# constraints
sess = Compile("test.onnx", buff_length=buff_length)
sess.solve()
res_2 = sess.sim(x)

# check the output is still the same
assert((res - res_2).sum() == 0)
print(res_2)

# delete generated model
import os
os.remove("test.onnx")
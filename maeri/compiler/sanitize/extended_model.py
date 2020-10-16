import onnx

class ExtendedModel():
    def __init__(self, model):
        self.__model = model
        self.graph = model.graph

        self.output_by_name = {}
        for output in model.graph.output:
            self.output_by_name[output.name] = output

        self.value_by_name = {}
        for value in model.graph.value_info:
            self.value_by_name[value.name] = value

        self.input_by_name = {}
        for input_ in model.graph.input:
            self.input_by_name[input_.name] = input_

        self.init_by_name = {}
        for init in model.graph.initializer:
            self.init_by_name[init.name] = init

    def __enter__(self):
        return self

    def __exit__(self ,type, value, traceback):
        pass

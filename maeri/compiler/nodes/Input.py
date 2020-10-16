class Input():
    def __init__(self, slice_, mem_ref):
        self.slice = slice_
        self.mem_ref = mem_ref

    def get_offset(self):
        raise NotImplementedError()

    def get_data(self):
        return self.mem_ref.data[self.slice]

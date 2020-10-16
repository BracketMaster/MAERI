class Output():
    def __init__(self, slice_, mem_ref):
        self.slice = slice_
        self.mem_ref = mem_ref

    def get_offset(self):
        raise NotImplementedError()

    def write_data(self, data):
        self.mem_ref.data[self.slice] = data

    def debug(self):
        return self.mem_ref.data[self.slice]

class Root():
    def __init__(self, slice_, mem_ref):
        self.mem_ref = mem_ref
        self.slice = slice_
    
    def split(self):
        pass
    
    def init_root(self, data):
        self.mem_ref.data[self.slice] = data

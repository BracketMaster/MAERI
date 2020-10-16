class Memory():
    def __init__(self, data):
        self.offset = None
        self.data = data # data is a Numpy array
    
    def get_offset(self, tuple_of_slices, shape):
        """
        Takes a tuple of slices and returns a dict of
        address offsets keys and slice values.
        """
        raise NotImplementedError()

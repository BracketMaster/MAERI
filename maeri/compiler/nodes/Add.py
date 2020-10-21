from maeri.common.logger import LogIndent, logger
from .Output import Output
from .Input import Input

class Add():
    def __init__(self, A, B, C):
        self.A = A
        self.B = B
        self.C = C
    
    def split(self):
        raise NotImplementedError()

    def sim(self):
        A = self.A.get_data()
        B = self.B.get_data()
        self.C.write_data(A + B)

        logger.debug("EXECUTING ADD")
        logger.debug(f"A = \n{A}")
        logger.debug(f"B = \n{B}")
        logger.debug(f"res = \n{A + B}")
    
    def split_to_buff_lengths(self, buff_length):
        length_A = self.A.slice[3].stop - self.A.slice[3].start
        length_B = self.B.slice[3].stop - self.B.slice[3].start

        # sanity check, this should really never be violated
        assert(length_A == length_B)
        length = length_A

        # we may not need to do any splitting
        if length <= buff_length:
            return [self]

        # split up adds
        op_graph = []
        splits, r = divmod(length, buff_length)
        for index in range(splits):
            offset_begin = index*buff_length
            offset_end = (index + 1)*buff_length

            slice_A = slice(self.A.slice[3].start + offset_begin, self.A.slice[3].start + offset_end)
            slice_A = (self.A.slice[0], self.A.slice[1], self.A.slice[2], slice_A)
            input_A = Input(slice_A, self.A.mem_ref)

            slice_B = slice(self.B.slice[3].start + offset_begin, self.B.slice[3].start + offset_end)
            slice_B = (self.B.slice[0], self.B.slice[1], self.B.slice[2], slice_B)
            input_B = Input(slice_B, self.B.mem_ref)

            slice_C = slice(self.C.slice[3].start + offset_begin, self.C.slice[3].start + offset_end)
            slice_C = (self.C.slice[0], self.C.slice[1], self.C.slice[2], slice_C)
            input_C = Output(slice_C, self.C.mem_ref)

            op_graph += [Add(input_A, input_B, input_C)]
        
        if r:
            offset_begin = splits*buff_length
            offset_end = length

            slice_A = slice(self.A.slice[3].start + offset_begin, self.A.slice[3].start + offset_end)
            slice_A = (self.A.slice[0], self.A.slice[1], self.A.slice[2], slice_A)
            input_A = Input(slice_A, self.A.mem_ref)

            slice_B = slice(self.B.slice[3].start + offset_begin, self.B.slice[3].start + offset_end)
            slice_B = (self.B.slice[0], self.B.slice[1], self.B.slice[2], slice_B)
            input_B = Input(slice_B, self.B.mem_ref)

            slice_C = slice(self.C.slice[3].start + offset_begin, self.C.slice[3].start + offset_end)
            slice_C = (self.C.slice[0], self.C.slice[1], self.C.slice[2], slice_C)
            input_C = Output(slice_C, self.C.mem_ref)

            op_graph += [Add(input_A, input_B, input_C)]

        return op_graph

    def split_to_ports(self, ports):
        depth_A = self.A.slice[2].stop - self.A.slice[2].start
        depth_B = self.B.slice[2].stop - self.B.slice[2].start

        # sanity check, this should really never be violated
        assert(depth_A == depth_B)
        depth = depth_A

        # we may not need to do any splitting
        if (depth*2) <= ports:
            return [self]

        # split up adds
        op_graph = []
        effective_ports = ports//2
        splits, r = divmod(depth, effective_ports)
        for index in range(splits):
            offset_begin = index*effective_ports
            offset_end = (index + 1)*effective_ports

            slice_A = slice(self.A.slice[2].start + offset_begin, self.A.slice[2].start + offset_end)
            slice_A = (self.A.slice[0], self.A.slice[1], slice_A, self.A.slice[3])
            input_A = Input(slice_A, self.A.mem_ref)

            slice_B = slice(self.B.slice[2].start + offset_begin, self.B.slice[2].start + offset_end)
            slice_B = (self.B.slice[0], self.B.slice[1], slice_B, self.B.slice[3])
            input_B = Input(slice_B, self.B.mem_ref)

            slice_C = slice(self.C.slice[2].start + offset_begin, self.C.slice[2].start + offset_end)
            slice_C = (self.C.slice[0], self.C.slice[1], slice_C, self.C.slice[3])
            input_C = Output(slice_C, self.C.mem_ref)

            op_graph += [Add(input_A, input_B, input_C)]
        
        if r:
            offset_begin = splits*effective_ports
            offset_end = depth

            slice_A = slice(self.A.slice[2].start + offset_begin, self.A.slice[2].start + offset_end)
            slice_A = (self.A.slice[0], self.A.slice[1], slice_A, self.A.slice[3])
            input_A = Input(slice_A, self.A.mem_ref)

            slice_B = slice(self.B.slice[2].start + offset_begin, self.B.slice[2].start + offset_end)
            slice_B = (self.B.slice[0], self.B.slice[1], slice_B, self.B.slice[3])
            input_B = Input(slice_B, self.B.mem_ref)

            slice_C = slice(self.C.slice[2].start + offset_begin, self.C.slice[2].start + offset_end)
            slice_C = (self.C.slice[0], self.C.slice[1], slice_C, self.C.slice[3])
            input_C = Output(slice_C, self.C.mem_ref)

            op_graph += [Add(input_A, input_B, input_C)]

        return op_graph

    
    def debug(self):
        A = self.A.get_data()
        B = self.B.get_data()
        C = self.C.debug()

        logger.debug("EXECUTING ADD")
        logger.debug(f"A = \n{A}")
        logger.debug(f"B = \n{B}")
        logger.debug(f"res = \n{C}")

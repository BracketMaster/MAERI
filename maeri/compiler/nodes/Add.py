from maeri.common.logger import LogIndent, logger

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
    
    def debug(self):
        A = self.A.get_data()
        B = self.B.get_data()
        C = self.C.debug()

        logger.debug("EXECUTING ADD")
        logger.debug(f"A = \n{A}")
        logger.debug(f"B = \n{B}")
        logger.debug(f"res = \n{C}")

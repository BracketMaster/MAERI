from maeri.common.logger import LogIndent, logger

def solve_for_buff_lengths(nodes, buff_length):
    solution = []
    for index in range(len(nodes)):
        node = nodes[index]
        input_width = (node.X.slice[3].stop - node.X.slice[3].start) + node.pad_left + node.pad_right
        if input_width > buff_length:
            solution += solve_for_buff_lengths(node.split_left_right(), buff_length)
        else:
            solution += [node]
    
    return solution

def solve_for_port_depth(nodes, ports):
    solution = []

    for node in nodes:
        solution += node.split_to_ports(ports)

    return solution

def debug_buff_lengths(nodes, buff_length):
    logger.debug("CHECKING BUFFER LENGTHS")
    conditions_list = []
    for node in nodes:
        input_width = (node.X.slice[3].stop - node.X.slice[3].start)
        conditions_list += [input_width <= buff_length]
    
    with LogIndent():
        logger.debug(conditions_list)

def verify_buff_Lengths(nodes, buff_length):
    for node in nodes:
        input_width = (node.X.slice[3].stop - node.X.slice[3].start) + node.pad_left + node.pad_right
        assert(input_width <= buff_length)

def solve_conv(node, buff_length, ports):
    logger.debug("CONV NODE")
    with LogIndent():

        logger.debug("BEFORE SOLVING CONV")
        debug_buff_lengths([node], buff_length)

        logger.debug("SOLVING FOR BUFFER LENGTH CONSTRAINT")
        solved_ops = solve_for_buff_lengths([node], buff_length)

        logger.debug("SOLVING FOR BUFFER NUM PORTS CONSTRAINT")
        solved_ops = solve_for_port_depth(solved_ops, ports)

        logger.debug("AFTER SOLVING CONV")
        debug_buff_lengths(solved_ops, buff_length)

        verify_buff_Lengths(solved_ops, buff_length)

        return solved_ops
from maeri.common.logger import LogIndent, logger

def solve_for_buff_lengths(nodes, buff_length):
    solution = []

    for node in nodes:
        solution += node.split_to_buff_lengths(buff_length)

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
        input_width = (node.A.slice[3].stop - node.A.slice[3].start)
        conditions_list += [input_width <= buff_length]
    
    with LogIndent():
        logger.debug(conditions_list)

#def debug_buff_lengths(nodes, buff_length):
#    logger.debug("CHECKING PORT DEPTHS SATISFIED")
#    conditions_list = []
#    for node in nodes:
#        input_width = (node.A.slice[3].stop - node.A.slice[3].start)
#        conditions_list += [input_width <= buff_length]
#    
#    with LogIndent():
#        logger.debug(conditions_list)

def verify_buff_length_satisfed(nodes, buff_length):
    for node in nodes:
        input_width_A = (node.A.slice[3].stop - node.A.slice[3].start)
        input_width_B = (node.B.slice[3].stop - node.B.slice[3].start)
        assert(input_width_A == input_width_B)
        if not (input_width_A <= buff_length):
            print(input_width_A)
            print(nodes)
        assert(input_width_A <= buff_length)
        assert(input_width_B <= buff_length)

def verify_port_depth_satisfied(nodes, ports):
    for node in nodes:
        input_depth_A = (node.A.slice[2].stop - node.A.slice[2].start)
        input_depth_B = (node.B.slice[2].stop - node.B.slice[2].start)
        assert(input_depth_A == input_depth_B)
        assert(input_depth_A*2 <= ports)
        assert(input_depth_B*2 <= ports)

def solve_add(node, buff_length, ports):
    logger.debug("ADD NODE")
    node_list = [node]
    with LogIndent():

        logger.debug("BEFORE SOLVING ADD")
        debug_buff_lengths(node_list, buff_length)

        logger.debug("SOLVING FOR BUFFER LENGTH CONSTRAINT")
        solved_ops = solve_for_buff_lengths(node_list, buff_length)
        verify_buff_length_satisfed(solved_ops, buff_length)

        logger.debug("SOLVING FOR BUFFER NUM PORTS CONSTRAINT")
        solved_ops = solve_for_port_depth(solved_ops, ports)
        verify_port_depth_satisfied(solved_ops, ports)

        debug_buff_lengths(solved_ops, buff_length)


        return solved_ops
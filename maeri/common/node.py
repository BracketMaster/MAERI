"""
Node class for binary tree.
"""

class Node:
	def __init__(self, id, latency):
		"""
		Latency has less to do with a binary tree than
		it does the micro-architectural implementation of a
		binary adder tree.

		There is a once cycle delay or latency between information
		that travels from a node on layer/generation x-1 to a node on
		layer/generation x on the binary tree, assuming that there is
		is a register between layers/generations of the micro-architectural
		implementation of the binary tree, which is the case for MAERI.

		Latency here is useful when considering how many cycles are needed
		for information to travel from the injection port to a particular node.
		"""
		self.id = id
		self.latency = latency
		self.lhs = None
		self.rhs = None
		self.parent = None
"""
Node class for binary tree.
"""

class Node:
	def __init__(self, id):
		self.id = id
		self.lhs = None
		self.rhs = None
		self.parent = None
"""
This file implements an array of memory
in a fashion that is useful to a compiler.

Memory() can allocate and free named variables.
This is useful during linking stage when
variables are replaced with addresses.

Example:
========
>>> mem = Memory(16, DEBUG=False)
>>> mem.allocate('a', 16)
>>> print(mem.get_region('a'))
(0, 15)
>>> mem.free('a')
>>> mem.allocate('a', 3) # allocate 3 bytes to a
>>> print(mem.get_region('a'))
(0, 2)
>>> mem.allocate('b', 5)
>>> mem.allocate('c', 4)
>>> mem.allocate('d', 4)
>>> mem.free('c')
>>> mem.free('a')
>>> mem.free('b')
>>> print(mem.get_region('d'))
(12, 15)
"""
class Memory():
    def __init__(self, mem_length, DEBUG=False):
        """
        Attributes:
        ===========
        self.DEBUG: print debugging information
        self.mem_length: total available memory region 
        in bytes

        self.unallocated: the free list which contains tuples
        for ranges of memory that are free in ascending
        order.

        Potential Runtime Snapshot:
            ```self.unallocated = [(0,30), (80, mem_length)]```
        
        self.allocated: keep track of what has already
        been allocated in the allocated list. 

        Potential Runtime Snapshot:
        ```
        self.allocated = [
            {
                'name' : 'some_var', 
                'region' : (start_addr, end_addr)
            }
            ]
        ```
        """

        self.DEBUG = DEBUG
        self.mem_length = mem_length
        self.unallocated = [(0, self.mem_length - 1)]
        self.allocated = {}
    
    def allocate(self, name, length):
        # length must be greater than 0
        if length <= 0:
            raise Exception(
                f"length for {name} must be greater than 0"
                )

        # verify var `name` is not already allocated
        if name in self.allocated.keys():
            raise Exception(f"var {name} already allocated.")

        # build a list of lengths of free regions.
        # such a list might look like:

        # length_by_free_region = [32, 64, 256, 28 32]
        length_by_free_regions = [
            (region[1] - region[0] + 1) for region in self.unallocated
        ]

        # find first free region of sufficient length if
        # any exist
        space_available = False
        for index, free_length in enumerate(length_by_free_regions):
            if length <= free_length:
                space_available = True
                break
        
        if not space_available:
            raise Exception("MAERI will need more than "
                + f"{self.mem_length} bytes to execute this neural"
                + "network."
                )
        
        # if free_length is the exact length requested,
        # delete that entry from the free list
        if length == free_length:
            start_addr = self.unallocated[index][0]
            end_addr = start_addr + length - 1
            self.allocated[name] = {'region' : (start_addr, end_addr)}
            del self.unallocated[index]
        
        else:
            # add region to allocated list
            start_addr = self.unallocated[index][0]
            end_addr = start_addr + length - 1
            self.allocated[name] = {'region' : (start_addr, end_addr)}
            
            # shrink region in free list
            free_start_addr = self.unallocated[index][0] + length
            free_end_addr = self.unallocated[index][1]
            new_range = (free_start_addr, free_end_addr)
            self.unallocated[index] = new_range

        if self.DEBUG:
            print(f"self.unallocated = {self.unallocated}")
            print(f"self.allocated = {self.allocated}")
        
    def free(self, name):
        """
        say we have self.unallocated = [(3,5), (8,11)]
        we want to deallocate region = (0, 2)
        we then get self.unallocated = [(0,2), (3,5), (8,11)]
        """

        if self.DEBUG:
            print("Attempting to deallocate")

        # verify var `name` is allocated
        if name not in self.allocated.keys():
            raise Exception(f"var {name} not allocated. " +
                             "Cannot be deallocated.")

        # get region that is to be deallocated and
        # returned to free list
        region = self.allocated[name]['region']

        # find where to insert deallocated region
        # into free list

        # special case of empty list
        if self.unallocated == []:
            self.unallocated = [region]

        else:
            returned = False
            for index, free_region in enumerate(self.unallocated):
                if region[1] < free_region[0]:
                    self.unallocated.insert(index, region)
                    returned = True
                    break
            
            if not returned:
                raise Exception(
                    "Error on deallocate. \n" +
                    f"Unable to place region {region} in free "
                    "list."
                    )
        
        # delete name from allocated list
        del self.allocated[name]

        
        if self.DEBUG:
            print(f"self.unallocated = {self.unallocated}")
            print(f"self.allocated = {self.allocated}")
        
        self.merge()
    
    def get_region(self, name):
        try:
            return self.allocated[name]['region']
        except:
            raise Exception(
                f"{name} does not appear to be allocated."
                )
    
    def merge(self, start_index=0):
        """
        say we have: 
        self.unallocated = [(a,b), (b+1, c), (d, e), (e+1, f)]
        after consolidate(), we have the following
        transformations:
        self.unallocated = [(a,b), (b+1, c), (d, e), (e+1, f)] ->
        self.unallocated = [(a,c), (d,e), (e+1, f)] ->
        self.unallocated = [(a,c), (d, f)]

        Parameters:
        ===========
        start_index: start attempting to merge tuples in the
        self.unallocated list from the provided `start_index` onwards
        """

        if self.DEBUG:
            print("Attempting Merge")
            print(f"self.unallocated = {self.unallocated}")

        if start_index == (len(self.unallocated) - 1):
            return

        # we grab a pair of ranges such as (a,b) and (b+1, c)
        f = self.unallocated
        left_pair, right_pair = f[start_index], f[start_index + 1]
        is_continuous = right_pair[0] - left_pair[1]

        # and we merge the pair if the ranges are continous
        if is_continuous == 1:
            if self.DEBUG:
                print("CONTINUOUS")
            new_range = left_pair[0], right_pair[1]
            del f[start_index]
            f[start_index] = new_range
            self.merge(start_index)
        else:
            self.merge(start_index+1)
def sorted_squares(nums):
    # Initialize two pointers: one at the beginning (left) and one at the end (right) of the array
    left = 0
    right = len(nums) - 1
    pos = right  # Start placing the largest squares from the end of the array

    # We'll use the nums array itself to store the sorted squares in-place
    while left <= right:
        left_square = nums[left] * nums[left]
        right_square = nums[right] * nums[right]
        
        if left_square > right_square:
            # If the left squared value is larger, place it at the 'pos' and move left pointer
            nums[pos] = left_square
            left += 1
        else:
            # Otherwise, place the right squared value and move right pointer
            nums[pos] = right_square
            right -= 1
        
        pos -= 1  # Move the position backward for the next largest square

    return nums

# Example usage
nums = [-4, -1, 0, 3, 10]
sorted_array = sorted_squares(nums)
print(sorted_array)

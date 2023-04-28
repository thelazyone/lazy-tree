import matplotlib.pyplot as plt
import numpy as np

import math

def avoid_ground(value, parameter):
    # Cubic function that maps -1 to 0 and 1 to 1
    def cubic_function(x):
        return (x + 1) ** 3 / 8

    # Interpolate between the original value and the cubic function result based on the parameter
    return value * (1 - parameter) + max(cubic_function(value),value) * parameter    
    
parameter = 1  # Adjust this value to see how it affects the function
values = np.linspace(-1, 1, 1000)
avoid_ground_values = [avoid_ground(value, parameter) for value in values]

plt.plot(values, avoid_ground_values)
plt.xlabel("Value")
plt.ylabel("Avoid Ground")
plt.title("Avoid Ground Function with parameter={}".format(parameter))
plt.grid(True)
plt.show()
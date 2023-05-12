import random
import math
from mathutils import Vector


def combine_lerp(value_bottom, value_top, parameter):
    # Expecting bottom to be 1 and top 0
    return value_bottom * parameter + value_top * (1 - parameter)

def combine_lerp_2D(values, parameter):
    return combine_lerp(values[0], values[1], parameter)
        
def cosine_sigmoid(x, min, max):
    if x < min: 
        return 0
    if x > max: 
        return 1
    size = max-min
    return (1 - math.cos((x - min) * math.pi / size)) / 2

def softplus(x, factor):
    return math.log(1 + math.exp(x * factor)) / factor

def uniform_random_direction():
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(0, math.pi)
    
    x = math.sin(phi) * math.cos(theta)
    y = math.sin(phi) * math.sin(theta)
    z = math.cos(phi)
    
    return Vector((x, y, z)).normalized()

import math
from math_functions import *


def get_thickness_parameter_base(tree_parameters, section):
    # The parameter is close to 1 when the element is thicker.
    initial_weight = tree_parameters.iterations
    parameter = section.weight / initial_weight
    return parameter

def get_thickness_parameter(tree_parameters, section):
    parameter = get_thickness_parameter_base(tree_parameters, section)
    
    # Applying a cosine sigmoid to the parameter.
    parameter = 1 - cosine_sigmoid(1 - parameter, tree_parameters.trunk_branches_division_2D[0], tree_parameters.trunk_branches_division_2D[1])

    # Adding another factor linked with the tree height. 
    max_height = 30
    section_height = section.points[0].z
    parameter = combine_lerp(1 - section_height/max_height, parameter, tree_parameters.tree_ground_factor)
    return parameter

def get_radius_from_weight(tree_parameters, section):
    radius_chunky_factor = math.pow(get_thickness_parameter_base(tree_parameters, section), tree_parameters.chunkyness)
    return  radius_chunky_factor * tree_parameters.radius
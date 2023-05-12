from tree_general_functions import *
from math_functions import *

def get_light_weight(section, iteration_number, tree_parameters):
    thickness = get_thickness_parameter_base(tree_parameters, section)
    light_searching = combine_lerp_2D(tree_parameters.light_searching_2D, thickness) + \
        tree_parameters.light_searching_fringes * (max(0, (1 -thickness)-0.95) * 5)
    return light_searching
import random
import math
from mathutils import Vector, Quaternion

from noise_displacements import *
from tree_general_functions import *
from tree_light_functions import *
from math_functions import uniform_random_direction
from tree_section import Section

def get_growth_direction(previous_point1, previous_point2, section, iteration_number, tree_parameters):
    direction = (previous_point2 - previous_point1).normalized()
    random_direction = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
    light_direction = Vector((\
        tree_parameters.light_source[0], \
        tree_parameters.light_source[1], \
        tree_parameters.light_source[2])).normalized()

    thickness = get_thickness_parameter_base(tree_parameters, section)
    noise_factor = combine_lerp_2D(tree_parameters.noise_2D, thickness) * 0.1

    final_direction = (direction + random_direction * noise_factor +\
            light_direction * get_light_weight(section, iteration_number, tree_parameters)* 0.01).normalized()
    return final_direction

def get_root_growth_direction(previous_point1, previous_point2, section, iteration_number, tree_parameters):
    direction = (previous_point2 - previous_point1).normalized()
    random_direction = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()

    # Noise factor is ideally higher than branhces.
    noise_factor = tree_parameters.roots_noise
    final_direction = (direction + random_direction * noise_factor).normalized()
    
    # Vertical directional factor depends on the closeness to zero.
    final_direction.z = final_direction.z * tree_parameters.roots_spread - previous_point1.z * (1 - tree_parameters.roots_spread)

    # Discouraging going towards origin:
    xy_position = Vector((previous_point1.x, previous_point1.y, 0)) 
    final_direction = final_direction + 0.05* xy_position.normalized() * final_direction.dot(xy_position)

    return final_direction.normalized()


def grow_step(sections, tree_parameters, iteration_number):
    for section in sections:
        if section.open_end:  
            
            # Checking for thickness
            radius = get_radius_from_weight(tree_parameters, section)

            if radius < tree_parameters.minimum_thickness / 2:
                section.open_end = False
                continue
            
            thickness_param = get_thickness_parameter(tree_parameters, section)
            segment_length = combine_lerp_2D(tree_parameters.segment_length_2D, thickness_param)
            last_point = section.points[-1]
            quasi_last_point = section.points[-2]
            new_point = last_point + get_growth_direction(\
                quasi_last_point, \
                last_point, \
                section, \
                iteration_number, \
                tree_parameters) *\
                segment_length
            section.points.append(new_point)
            section.distance = section.distance + 1

def grow_root(root_sections, tree_parameters, iteration_number):
    for section in root_sections:
        if section.open_end:  
            
            # Checking for thickness
            radius = get_radius_from_weight(tree_parameters, section)

            if radius < tree_parameters.minimum_thickness / 2:
                section.open_end = False
                continue
            
            segment_length = tree_parameters.root_segment_length
            last_point = section.points[-1]
            quasi_last_point = section.points[-2]
            new_point = last_point + get_root_growth_direction(\
                quasi_last_point, \
                last_point, \
                section, \
                iteration_number, \
                tree_parameters) *\
                segment_length
            section.points.append(new_point)
            section.distance = section.distance + 1

def check_splits(sections, tree_parameters, iteration_number):
    
    new_sections = []
    for counter, section in enumerate(sections):
        thickness_param = get_thickness_parameter(tree_parameters, section)
        min_length = combine_lerp_2D(tree_parameters.min_length_2D, thickness_param)
        split_chance = combine_lerp_2D(tree_parameters.split_chance_2D, thickness_param)
        segment_length = combine_lerp_2D(tree_parameters.segment_length_2D, thickness_param)
        split_chance = split_chance * segment_length
        section_length = section.distance
        if section.parent is not None:
            section_length = section_length - section.parent.distance
        chance_factor = (section_length * segment_length / min_length)
        if section.open_end and random.random() < split_chance * chance_factor:
            
            if (section_length < min_length):
                continue

            # A split is happening: the current section is not open-ended anymore.
            section.open_end = False

            # Direction is provided by the last segment in the section. Sections start with
            # two points so we can assume that there are at least 2 points here.
            initial_direction = get_growth_direction(
                section.points[-2], 
                section.points[-1], 
                section,
                iteration_number,
                tree_parameters)

            # Calculating the weight of the two branches. The distribution goes from 0 to
            # 0.5 (equal split). the new branch is always the smaller one.
            split_ratio = combine_lerp_2D(tree_parameters.split_ratio_2D, thickness_param)
            split_ratio = combine_lerp(random.uniform(0,1), split_ratio, tree_parameters.split_ratio_random) 
                
            new_section1 = Section( \
                points=section.points[-1:], \
                depth=section.depth + 1, \
                distance = section.distance + 1, \
                weight=section.weight * (1 - split_ratio), \
                open_end=True, \
                parent=section,
                parent_id=counter,
                is_root=section.is_root)
            new_section2 = Section( \
                points=section.points[-1:], \
                depth=section.depth + 1, \
                distance = section.distance + 1, \
                weight=section.weight * (split_ratio), \
                open_end=True, \
                parent=section,
                parent_id=counter,
                is_root=section.is_root)

            # Rotating the branches along a random direction. The split is handled
            # through the split_ratio parameter before. 
            direction1 = initial_direction.copy()
            direction2 = initial_direction.copy()
            random_direction = uniform_random_direction()

            # Angles should depend on the weight of the subsection.
            split_angle = tree_parameters.split_angle + \
                random.uniform(-1, 1) * tree_parameters.split_angle_randomness
            angle1 = -split_angle * split_ratio * (new_section1.weight / section.weight * 2)
            angle2 = split_angle * (1 - split_ratio) * (new_section1.weight / section.weight * 2)
            split_rotation = math.radians(random.uniform(0, 2 * math.pi))

            direction1.rotate(Quaternion(direction1.cross(random_direction).normalized(), math.radians(angle1)))
            direction1.rotate(Quaternion(initial_direction.normalized(), split_rotation))
            direction2.rotate(Quaternion(direction2.cross(random_direction).normalized(), math.radians(angle2)))
            direction2.rotate(Quaternion(initial_direction.normalized(), split_rotation))

            # Now calculating the effects on the new direction, then adding it to the new sections.
            new_section1.points.extend([new_section1.points[-1] + \
                get_branches_direction(direction1, new_section1, tree_parameters, iteration_number) *\
                    segment_length])
            new_section2.points.extend([new_section2.points[-1] + \
                get_branches_direction(direction2, new_section2, tree_parameters, iteration_number) *\
                    segment_length])
                    
            new_sections.extend([new_section1, new_section2])

    return new_sections

def get_branches_direction(direction, section, tree_parameters, iteration_number):
    # Combining the random direction with the light direction
    light_direction = Vector((tree_parameters.light_source[0], tree_parameters.light_source[1], tree_parameters.light_source[2])).normalized()
    
    # Gravity depends on how much the branch weight is.
    root_weight = tree_parameters.iterations
    gravity_direction = Vector((0, 0, -1))
    gravity_strength = tree_parameters.trunk_gravity * section.weight / root_weight
    gravity_vector = gravity_strength * gravity_direction * Vector((direction.x, direction.y, 0)).length
    
    # Light Searching parameter
    light_searching = get_light_weight(section, iteration_number, tree_parameters)

    # Adding the various effects and normalizing.
    direction = direction + \
        light_direction * light_searching * 0.1 + \
        gravity_vector
    direction = direction.normalized()

    # Avoiding ground means that all negative Z values of direction are mitigated.
    direction.z = avoid_ground(direction.z, tree_parameters.ground_avoiding)
    return direction.normalized()
    
def avoid_ground(value, parameter):
    
    # Interpolate between the original value and the sigmoid
    return combine_lerp(softplus(value, 6), value, parameter)  

def apply_noise(sections, tree_parameters): 
    new_sections = []
    for section in sections:

        # Applying the noise factor now. 
        thickness = get_thickness_parameter(tree_parameters, section)
        noise_scale=combine_lerp_2D(tree_parameters.noise_scale_2D, thickness)
        noise_intensity=combine_lerp_2D(tree_parameters.noise_intensity_2D, thickness)
        new_points = []
        for point in section.points: 
            new_points.append(displace_point_with_noise(point, noise_intensity, noise_scale))
            #temp_section.points.append(point)
        section.points = new_points
        
        # Translating the section to the position of the parent last point
        if section.parent is not None:
            parent_last_point = sections[section.parent_id].points[-1]
            translation_vector = section.points[0] - parent_last_point
            new_points = []
            for point in section.points:
                new_points.append(point - translation_vector)
            section.points = new_points

    return sections

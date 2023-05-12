import bpy
import bmesh

from mathutils import Vector
from noise_displacements import *
from tree_general_functions import *
from tree_light_functions import *
from math_functions import *

def create_circle_verts(position, direction, radius, point_distance, thickness_parameter, tree_parameters):
    circle_verts = []

    # Compute an orthogonal basis for the circle's plane
    up = Vector((1, 0, 0))
    if abs(direction.dot(up)) > 0.99:
        up = Vector((0, 0, 1))
    side = direction.cross(up).normalized()
    up = side.cross(direction).normalized()

    # Determine the initial angle based on the direction
    initial_angle = math.atan2(direction.y, direction.x)
                
    thickness = thickness_parameter
    surface_noise_planar = combine_lerp_2D(tree_parameters.surface_noise_planar_2D, thickness)
    surface_noise_vertical = combine_lerp_2D(tree_parameters.surface_noise_vertical_2D, thickness)
    surface_noise_intensity = combine_lerp_2D(tree_parameters.surface_noise_intensity_2D, thickness)
    section_step_length = combine_lerp_2D(tree_parameters.segment_length_2D, thickness)

    for i in range(tree_parameters.branch_resolution):
        angle = (2 * math.pi / tree_parameters.branch_resolution) * i + initial_angle
        radius_noise = get_radius_noise(angle, surface_noise_planar, \
                                        surface_noise_vertical * point_distance)
        
        vertex = position + combine_lerp(radius, radius*radius_noise, 1-surface_noise_intensity) *\
                (math.cos(angle) * side + math.sin(angle) * up)
        circle_verts.append(vertex)

    return circle_verts

def create_section_mesh(section, tree_parameters):
    thickness = get_thickness_parameter_base(tree_parameters, section)
    if section.parent is None:
        if not section.is_root:
            radius = tree_parameters.radius
        else:
            radius = get_radius_from_weight(tree_parameters, section)
        parent_radius = radius
        parent_distance = 0
        parent_thickness = thickness
    else:
        radius = get_radius_from_weight(tree_parameters, section)
        parent_radius =  get_radius_from_weight(tree_parameters, section.parent)
        parent_distance = section.parent.distance
        parent_thickness = get_thickness_parameter_base(tree_parameters, section.parent)

    mesh = bpy.data.meshes.new("Branch")
    bm = bmesh.new()

    previous_circle_verts = None
    bottom_bm_edges = None
    reference_point = None
    
    for i in range(len(section.points)):
        current_point = section.points[i]
        direction = Vector((0,0,1))
        if i > 1: 
            prev_point = section.points[i - 1]
            direction = (current_point - prev_point).normalized()

        # Calculate the lerp factor based on the current index in the section points
        # With a minimum lerping value of 0.05 to prevent extreme cases.
        lerp_limit = max(0.05, math.sqrt(radius / parent_radius))
        lerp_factor = cosine_sigmoid(i / (len(section.points) - 1), 0.0, lerp_limit)
        
        # If the section has a parent, modify the direction and radius
        lerped_radius = radius
        if section.parent:
            parent_end_direction = (section.parent.points[-1] - section.parent.points[-2]).normalized()
            direction = direction.lerp(parent_end_direction, 1-lerp_factor)
            lerped_radius = combine_lerp(radius, parent_radius, lerp_factor)

            # Calculate the parent's point position projected onto the lerped direction
            if i == 0:
                reference_point = section.parent.points[-1]
            projected_point = reference_point + (direction * (current_point - reference_point).dot(direction))
            reference_point = projected_point
            
            # Interpolate between the current point position and the projected point position
            lerped_position = current_point.lerp(projected_point, 1-lerp_factor)
            
        else:
            lerped_position = current_point

        # For the noise we need a smarter way to use the thickness through lerping
        lerped_thickness = combine_lerp(thickness, parent_thickness, lerp_factor)
        lerped_thickness = math.sqrt(lerped_thickness)
        point_distance = parent_distance + i
        current_circle_verts = create_circle_verts(
            lerped_position, direction, lerped_radius, point_distance, lerped_thickness, tree_parameters
        )
        
        # Creating this loop's vertices and edges:
        bm_verts = []
        for j in range(tree_parameters.branch_resolution):
            bm_verts.append(bm.verts.new(current_circle_verts[j]))

        bm_edges = []
        for j in range(tree_parameters.branch_resolution):
            v0 = bm_verts[j]
            v1 = bm_verts[(j + 1) % tree_parameters.branch_resolution]
            if (v0, v1) not in bm.edges and (v1, v0) not in bm.edges:
                bm_edges.append(bm.edges.new([v0, v1]))

        # If none, filling the bottom.
        if previous_circle_verts is None: 
            bmesh.ops.contextual_create(bm, geom=bm_verts)

        # else, calling bridge loop    
        if previous_circle_verts is not None:
            edge_loops = bottom_bm_edges + bm_edges
            bmesh.ops.bridge_loops(bm, edges=edge_loops)
            
        # If last element, closing.
        if i == len(section.points) - 1:
            bmesh.ops.contextual_create(bm, geom=bm_verts)

        previous_circle_verts = current_circle_verts
        bottom_bm_verts = bm_verts.copy()
        bottom_bm_edges = bm_edges.copy()

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    return mesh
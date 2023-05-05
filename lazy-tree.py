bl_info = {
    "name": "Lazy Tree",
    "author": "thelazyone - Giacomo pantalone",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "View3D > Sidebar > Create",
    "description": "Generate tree meshes, from the ground up",
    "warning": "",
    "doc_url": "",
    "category": "Add Mesh",
}


import bpy
import bmesh
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty

# for split logic.
import random
import math

# TODO add seed for noise!
from mathutils import Vector, Quaternion, Matrix, noise

 
# General Functions:
def displace_point_with_noise(point, intensity, scale):
    # Convert the point's position to a coordinate in noise space
    noise_coord = point * scale

    # Sample the 3D Perlin noise using the noise_coord
    noise_value_x = noise.noise(noise_coord)
    noise_value_y = noise.noise(noise_coord + Vector((100,100,100)))
    noise_value_z = noise.noise(noise_coord + Vector((100,200,200)))

    # Create a displacement vector with the noise_value multiplied by intensity
    displacement = Vector((noise_value_x, noise_value_y, noise_value_z)) * intensity

    # Add the displacement vector to the original point's position
    displaced_point = point + displacement

    return displaced_point

def get_radius_noise(angle_rad, planar_scale, offset):
    # Translate 
    noise_coord = Vector((math.sin(angle_rad), math.cos(angle_rad), offset));
    return noise.noise(noise_coord * planar_scale)

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

class Section:
    def __init__(self, points, depth, distance, weight, open_end=True, parent=None, parent_id=None):
        self.points = points
        self.open_end = open_end
        self.depth = depth
        self.distance = distance
        self.weight = weight
        self.parent = parent
        self.parent_id = parent_id
        
def update_tree(self, context):
    bpy.ops.growtree.create_tree()

# Blender classes:        
class GROWTREE_PG_tree_parameters(bpy.types.PropertyGroup):

    # General Properties
    seed: bpy.props.IntProperty(name="Seed", default=0, update=update_tree)
    iterations: bpy.props.IntProperty(name="Iterations", default=20, min=0, max=1024, update=update_tree)
    radius: bpy.props.FloatProperty(name="Trunk Base Radius", default=0.5, min=0.1, max=10, update=update_tree)
    trunk_branches_division: bpy.props.FloatVectorProperty(name="Trunk Branches divisions", default=(0.2, 0.8), min = 0, max = 1, size=2, update=update_tree)

    # Branching
    split_chance_2D: bpy.props.FloatVectorProperty(name="Split Chance %", default=(0.5, 1), min = 0, max = 10, size=2, update=update_tree)
    split_angle: bpy.props.FloatProperty(name="Split Angle (deg)", default=45, min=0, max=90, update=update_tree)
    split_angle_randomness: bpy.props.FloatProperty(name="Split Angle Randomness (deg)", default=10, min=0, max=90, update=update_tree)
    split_ratio_2D: bpy.props.FloatVectorProperty(name="Branch Split Ratio", default=(0.4, 0.1), min=0.1, max=0.5, size=2, update=update_tree)
    split_ratio_random: bpy.props.FloatProperty(name="Branch Split Ratio Randomness", default=0.1, min=0, max=1,  update=update_tree)
    segment_length_2D: bpy.props.FloatVectorProperty(name="Segment Length", default=(0.1, 0.1), min=0, max=10, size=2, update=update_tree)
    tree_ground_factor: bpy.props.FloatProperty(name="Ground Trunk Factor", default=0.2, min=0, max=1, update=update_tree)
    min_length_2D: bpy.props.FloatVectorProperty(name="Average Lenght", default=(10, 5), min=1, max=100, size=2, update=update_tree)

    # Deformation
    light_source: bpy.props.FloatVectorProperty(name="Light Source", default=(0, 0, 100), update=update_tree)
    light_searching_2D: bpy.props.FloatVectorProperty(name="Light Searching", default=(0.5, 0.5), min=0, max=2, size=2, update=update_tree)
    light_searching_fringes: bpy.props.FloatProperty(name="Light Searching Fringes", default=3, min=0, max=10, update=update_tree)
    ground_avoiding: bpy.props.FloatProperty(name="Ground Avoiding", default=0.5, min=0, max=5, update=update_tree)
    trunk_gravity: bpy.props.FloatProperty(name="Trunk Gravity", default=0.2, min=0, max=1, update=update_tree)
    noise_2D: bpy.props.FloatVectorProperty(name="Growth Noise", default=(0.5, 0.5), min=0, max=10, size=2, update=update_tree)
    noise_scale_2D: bpy.props.FloatVectorProperty(name="Volumetric Noise Scale", default=(1, 0.2), min=0.01, max=5, size=2, update=update_tree)
    noise_intensity_2D: bpy.props.FloatVectorProperty(name="Volumetric Noise Intensity", default=(1, 0.2), min=0.01, max=5, size=2, update=update_tree)

    # Meshing
    generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=False, update=update_tree)
    branch_resolution: bpy.props.IntProperty(name="Branch Resolution", default=8, min=3, max=32, update=update_tree)
    minimum_thickness: bpy.props.FloatProperty(name="Min Thickness", default=0.05, min=0.01, max=0.5, update=update_tree)
    chunkyness: bpy.props.FloatProperty(name="Chunkyness", default=0.5, min=0.1, max=2, update=update_tree)
    surface_noise_planar: bpy.props.FloatVectorProperty(name="Surface Planar Noise Scale", default=(0.4, 0.2), min=0.01, max=5, size=2, update=update_tree)
    surface_noise_vertical: bpy.props.FloatVectorProperty(name="Surface Vertical Noise Scale", default=(0.4, 0.2), min=0.01, max=5, size=2, update=update_tree)
    surface_noise_intensity: bpy.props.FloatVectorProperty(name="Surface Noise Intensity", default=(0.4, 0.2), min=0.01, max=5, size=2, update=update_tree)


class GROWTREE_OT_create_tree(bpy.types.Operator):
    bl_idname = "growtree.create_tree"
    bl_label = "Create Tree"
    bl_options = {'REGISTER', 'UNDO'}

    tree_parameters: bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)

    def execute(self, context):
        tree_parameters = context.scene.tree_parameters

        # TODO decomment this when a proper estimation of the segments is feasible!                        
        # # Before calculating a new tree, making sure that the amount of segments isn't 
        # # likely to exceed a certain amount. let's say 10000.
        # max_segments = 100000 
        # est_segments = pow(1 + tree_parameters.split_chance * 0.01, tree_parameters.iterations)
        # if  est_segments > max_segments:
        #     self.report({'WARNING'}, \
        #         f"Estimated number of segments ({int(est_segments)}) exceeds the limit ({max_segments}). Aborting.")
        #     return {'CANCELLED'}
        
        mesh = self.create_tree_mesh(tree_parameters)
        obj_name = "Created Tree"
        
        # Unlink and remove the old object if it exists
        if obj_name in bpy.data.objects:
            old_obj = bpy.data.objects[obj_name]
            if old_obj.name in context.collection.objects:
                context.collection.objects.unlink(old_obj)
            bpy.data.objects.remove(old_obj)

        # Create a new object and link it to the scene
        obj = bpy.data.objects.new(obj_name, mesh)
        context.collection.objects.link(obj)

        return {'FINISHED'}


    def create_tree_mesh(self, tree_parameters):
        
        random.seed(tree_parameters.seed)
        
        def get_light_weight(section, iteration_number, tree_parameters):
            thickness = get_thickness_parameter_base(tree_parameters, section)
            light_searching = combine_lerp_2D(tree_parameters.light_searching_2D, thickness) + \
                tree_parameters.light_searching_fringes * (max(0, (1 -thickness)-0.95) * 5)
            return light_searching
        
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

        def get_thickness_parameter_base(tree_parameters, section):
            # The parameter is close to 1 when the element is thicker.
            initial_weight = tree_parameters.iterations
            parameter = section.weight / initial_weight
            return parameter

        def get_thickness_parameter(tree_parameters, section):
            parameter = get_thickness_parameter_base(tree_parameters, section)
            
            # Applying a cosine sigmoid to the parameter.
            parameter = 1 - cosine_sigmoid(1 - parameter, tree_parameters.trunk_branches_division[0], tree_parameters.trunk_branches_division[1])

            # Adding another factor linked with the tree height. 
            max_height = 30
            section_height = section.points[0].z
            parameter = combine_lerp(1 - section_height/max_height, parameter, tree_parameters.tree_ground_factor)
            return parameter
        
        def get_radius_from_weight(tree_parameters, section):
            radius_chunky_factor = math.pow(get_thickness_parameter_base(tree_parameters, section), tree_parameters.chunkyness)
            return  radius_chunky_factor * tree_parameters.radius

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
                        parent_id=counter)
                    new_section2 = Section( \
                        points=section.points[-1:], \
                        depth=section.depth + 1, \
                        distance = section.distance + 1, \
                        weight=section.weight * (split_ratio), \
                        open_end=True, \
                        parent=section,
                        parent_id=counter)

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
            surface_noise_planar = combine_lerp_2D(tree_parameters.surface_noise_planar, thickness)
            surface_noise_vertical = combine_lerp_2D(tree_parameters.surface_noise_vertical, thickness)
            #surface_noise_vertical = tree_parameters.surface_noise_vertical[0]
            surface_noise_intensity = combine_lerp_2D(tree_parameters.surface_noise_intensity, thickness)
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
                radius = tree_parameters.radius
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
        
        mesh = bpy.data.meshes.new("Tree")
        bm = bmesh.new()

        root_section = Section( \
            points=[Vector((0, 0, 0)),Vector((0, 0, 0.1))], \
            weight=tree_parameters.iterations, \
            depth=1,\
            distance=1)
        sections = [root_section]

        # Growing iterations!
        for iteration_number in range(tree_parameters.iterations):
            grow_step(sections, tree_parameters, iteration_number)
            new_sections = check_splits(sections, tree_parameters, iteration_number)
            sections.extend(new_sections)

        # Applying Noise 
        sections = apply_noise(sections, tree_parameters)

        # Creating main mesh
        mesh = bpy.data.meshes.new("Tree")
        bm = bmesh.new()

        if tree_parameters.generate_mesh:
            section_matrix = Matrix.Identity(4)
            
            # Generate mesh with cylinders
            for section in sections:
                section_mesh = create_section_mesh(section, tree_parameters)
                temp_bm = bmesh.new()
                temp_bm.from_mesh(section_mesh)
                temp_bm.transform(section_matrix)
                bmesh.ops.transform(temp_bm, matrix=section_matrix, verts=temp_bm.verts)
                bmesh.ops.contextual_create(temp_bm, geom=temp_bm.edges)
                vertex_map = {}

                for v in temp_bm.verts:
                    new_vert = bm.verts.new(v.co)
                    vertex_map[v.index] = new_vert
                bm.verts.ensure_lookup_table()

                for e in temp_bm.edges:
                    bm.edges.new([vertex_map[e.verts[0].index], vertex_map[e.verts[1].index]])
                bm.edges.ensure_lookup_table()

                for f in temp_bm.faces:
                    bm.faces.new([vertex_map[v.index] for v in f.verts])  # Add this line
                bm.faces.ensure_lookup_table()  # Add this line

                temp_bm.free()

        else:
            # Generate mesh with segments
            for section in sections:
                v0 = bm.verts.new(section.points[0])
                for i in range(len(section.points) - 1):
                    v1 = bm.verts.new(section.points[i + 1])
                    bm.edges.new([v0, v1])
                    v0 = v1

        bm.to_mesh(mesh)  # Keep this line
        bm.free()  # Keep this line


        return mesh

class GROWTREE_PT_create_tree_panel(bpy.types.Panel):
    bl_label = "Grow Tree"
    bl_idname = "GROWTREE_PT_create_tree_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Create'

    def draw(self, context):
        layout = self.layout
        tree_parameters = context.scene.tree_parameters

        for prop_name in GROWTREE_PG_tree_parameters.__annotations__.keys():
            layout.prop(tree_parameters, prop_name)

        layout.operator(GROWTREE_OT_create_tree.bl_idname)

def menu_func(self, context):
    self.layout.operator(GROWTREE_OT_create_tree.bl_idname)


def register():
    bpy.utils.register_class(GROWTREE_PG_tree_parameters)
    bpy.utils.register_class(GROWTREE_OT_create_tree)
    bpy.utils.register_class(GROWTREE_PT_create_tree_panel)
    bpy.types.Scene.tree_parameters = bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_class(GROWTREE_PG_tree_parameters)
    bpy.utils.unregister_class(GROWTREE_OT_create_tree)
    bpy.utils.unregister_class(GROWTREE_PT_create_tree_panel)
    del bpy.types.Scene.tree_parameters
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
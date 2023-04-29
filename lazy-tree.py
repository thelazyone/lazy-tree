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
from mathutils import Vector, Quaternion, Matrix


class Section:
    def __init__(self, points, depth, length, weight, open_end=True, parent=None):
        self.points = points
        self.open_end = open_end
        self.depth = depth
        self.length = length
        self.weight = weight
        self.parent = parent
        
def update_tree(self, context):
    bpy.ops.growtree.create_tree()

# Blender classes:        
class GROWTREE_PG_tree_parameters(bpy.types.PropertyGroup):
    seed: bpy.props.IntProperty(name="Seed", default=0, update=update_tree)
    iterations: bpy.props.IntProperty(name="Iterations", default=20, min=0, max=1024, update=update_tree)
    segment_length:  bpy.props.FloatProperty(name="Segment Length", default=0.1, min=0, max=10, update=update_tree)
    radius: bpy.props.FloatProperty(name="Trunk Radius", default=0.5, min=0.1, max=10, update=update_tree)
    split_chance: bpy.props.FloatProperty(name="Split Chance %", default=5, min=0, max=10, update=update_tree)
    split_angle: bpy.props.FloatProperty(name="Split Angle", default=45, min=0, max=90, update=update_tree)
    light_source: bpy.props.FloatVectorProperty(name="Light Source", default=(0, 0, 1000), update=update_tree)
    light_searching_top: bpy.props.FloatProperty(name="Light Searching Top", default=0.5, min=0, max=2, update=update_tree)
    light_searching_bottom: bpy.props.FloatProperty(name="Light Searching Bottom", default=0.5, min=0, max=2, update=update_tree)
    light_searching_edges: bpy.props.FloatProperty(name="Light Searching Fringes", default=3, min=0, max=10, update=update_tree)
    ground_avoiding: bpy.props.FloatProperty(name="Ground Avoiding", default=0.5, min=0, max=3, update=update_tree)
    trunk_gravity: bpy.props.FloatProperty(name="Trunk Gravity", default=0.5, min=0, max=10, update=update_tree)
    split_ratio_bottom: bpy.props.FloatProperty(name="Branch Split Ratio Bottom", default=0.4, min=0, max=0.5, update=update_tree)
    split_ratio_top: bpy.props.FloatProperty(name="Branch Split Ratio Top", default=0.1, min=0, max=0.5, update=update_tree)
    split_ratio_random: bpy.props.FloatProperty(name="Branch Split Ratio Randomness", default=0.1, min=0, max=1, update=update_tree)
    tree_weight_factor: bpy.props.FloatProperty(name="Tree Weight", default=10, min=1, max=50, update=update_tree)
    min_length_bottom: bpy.props.FloatProperty(name="Bottom Sections Lenght", default=10, min=1, max=100, update=update_tree)
    min_length_top: bpy.props.FloatProperty(name="Top Sections Lenght", default=5, min=1, max=100, update=update_tree)
    generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=False, update=update_tree)
    branch_resolution: bpy.props.IntProperty(name="Branch Resolution", default=8, min=3, max=32, update=update_tree)
    minimum_thickness: bpy.props.FloatProperty(name="Min Thickness", default=0.05, min=0.01, max=0.5, update=update_tree)
    
class GROWTREE_OT_create_tree(bpy.types.Operator):
    bl_idname = "growtree.create_tree"
    bl_label = "Create Tree"
    bl_options = {'REGISTER', 'UNDO'}

    tree_parameters: bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)

    def execute(self, context):
        tree_parameters = context.scene.tree_parameters
                        
        # Before calculating a new tree, making sure that the amount of segments isn't 
        # likely to exceed a certain amount. let's say 10000.
        max_segments = 100000 
        est_segments = pow(1 + tree_parameters.split_chance * 0.01, tree_parameters.iterations)
        if  est_segments > max_segments:
            self.report({'WARNING'}, \
                f"Estimated number of segments ({int(est_segments)}) exceeds the limit ({max_segments}). Aborting.")
            return {'CANCELLED'}
        
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
    
        def get_random_value(seed):
            random.seed(seed)
            return random.random()
        
        def get_light_weight(section_weight, iteration_number, tree_parameters):
             # Light Searching parameter
            progress = iteration_number / tree_parameters.iterations
            root_weight = tree_parameters.tree_weight_factor * tree_parameters.iterations
            thickness = math.sqrt(1 - section_weight / root_weight)
            light_searching = \
                tree_parameters.light_searching_bottom * (1 - progress) + \
                tree_parameters.light_searching_top * progress + \
                tree_parameters.light_searching_edges * (max(0, thickness-0.97) * 5)
            return light_searching
        
        def get_growth_direction(previous_point1, previous_point2, section_weight, iteration_number, tree_parameters):
            direction = (previous_point2 - previous_point1).normalized()
            random_direction = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
            light_direction = Vector((\
                tree_parameters.light_source[0], \
                tree_parameters.light_source[1], \
                tree_parameters.light_source[2])).normalized()

            final_direction = (direction + random_direction * 0.05 +\
                 light_direction * get_light_weight(section_weight, iteration_number, tree_parameters)* 0.01).normalized()
            return final_direction

        def grow_step(sections, tree_parameters, iteration_number):
            for section in sections:
                if section.open_end:  
                    
                    # Checking for thickness
                    initial_weight = tree_parameters.tree_weight_factor * tree_parameters.iterations
                    radius = math.sqrt(section.weight / initial_weight) * tree_parameters.radius
                    if radius < tree_parameters.minimum_thickness / 2:
                        section.open_end = False
                        continue
                    
                    section.length = section.length + 1
                    last_point = section.points[-1]
                    quasi_last_point = section.points[-2]
                    new_point = last_point + get_growth_direction(\
                        quasi_last_point, \
                        last_point, \
                        section.weight, \
                        iteration_number, \
                        tree_parameters) *\
                        tree_parameters.segment_length
                    section.points.append(new_point)

        def check_splits(sections, tree_parameters, iteration_number):
            
            # Progress indicates how far in the simulation we are. 
            # Variable with "bottom" and "top" will be combined based on this.
            progress = iteration_number / tree_parameters.iterations
            min_length = tree_parameters.min_length_bottom * (1 - progress) + \
                tree_parameters.min_length_top * progress
                
            new_sections = []
            for section in sections:
                
                chance_factor = math.exp(section.length - min_length) - 1
                if section.open_end and random.random() < tree_parameters.split_chance * 0.01 * chance_factor:
                    
                    root_weight = tree_parameters.tree_weight_factor * tree_parameters.iterations
                    thickness_param = math.sqrt(1 - section.weight / root_weight)
                    min_length = tree_parameters.min_length_bottom * (1 - thickness_param) + \
                        tree_parameters.min_length_top * thickness_param
                    if (section.length < min_length):
                        continue

                    # A split is happening: the current section is not open-ended anymore.
                    section.open_end = False

                    # Direction is provided by the last segment in the section. Sections start with
                    # two points so we can assume that there are at least 2 points here.
                    initial_direction = get_growth_direction(
                        section.points[-2], 
                        section.points[-1], 
                        section.weight,
                        iteration_number,
                        tree_parameters)

                    # Calculating the weight of the two branches. The distribution goes from 0 to
                    # 0.5 (equal split). the new branch is always the smaller one.
                    progress = iteration_number / tree_parameters.iterations
                    # split_ratio = \
                    #     tree_parameters.split_ratio_bottom * (1 - progress) + \
                    #     tree_parameters.split_ratio_top * progress
                    split_ratio = \
                        tree_parameters.split_ratio_bottom * (1 - thickness_param) + \
                        tree_parameters.split_ratio_top * thickness_param
                    split_ratio = split_ratio * (1 - tree_parameters.split_ratio_random) + \
                        random.uniform(0.,1.) * tree_parameters.split_ratio_random 
                        
                    new_section1 = Section( \
                        points=section.points[-1:], \
                        depth=section.depth + 1, \
                        length= 1, \
                        weight=section.weight * (1 - split_ratio), \
                        open_end=True, \
                        parent=section)
                    new_section2 = Section( \
                        points=section.points[-1:], \
                        depth=section.depth + 1, \
                        length= 1, \
                        weight=section.weight * (split_ratio), \
                        open_end=True, \
                        parent=section)

                    # Rotating the branches along a random direction. The split is handled
                    # through the split_ratio parameter before. 
                    direction1 = initial_direction.copy()
                    direction2 = initial_direction.copy()
                    random_direction = uniform_random_direction()
                    angle1 = -tree_parameters.split_angle * split_ratio
                    angle2 = tree_parameters.split_angle * (1 - split_ratio)
                    direction1.rotate(Quaternion(direction1.cross(random_direction).normalized(), math.radians(angle1)))
                    direction2.rotate(Quaternion(direction2.cross(random_direction).normalized(), math.radians(angle2)))

                    # Now calculating the effects on the new direction, then adding it to the new sections.
                    new_section1.points.extend([new_section1.points[-1] + \
                        get_branches_direction(direction1, new_section1, tree_parameters, iteration_number) *\
                            tree_parameters.segment_length])
                    new_section2.points.extend([new_section2.points[-1] + \
                        get_branches_direction(direction2, new_section2, tree_parameters, iteration_number) *\
                            tree_parameters.segment_length])
                            
                    new_sections.extend([new_section1, new_section2])

            return new_sections

        def get_branches_direction(direction, section, tree_parameters, iteration_number):
            # Combining the random direction with the light direction
            light_direction = Vector((tree_parameters.light_source[0], tree_parameters.light_source[1], tree_parameters.light_source[2])).normalized()
            
            # Gravity depends on how much the branch weight is.
            root_weight = tree_parameters.tree_weight_factor * tree_parameters.iterations
            gravity_direction = Vector((0, 0, -1))
            gravity_strength = tree_parameters.trunk_gravity * section.weight / root_weight
            gravity_vector = gravity_strength * gravity_direction * Vector((direction.x, direction.y, 0)).length
            
            # Light Searching parameter
            progress = iteration_number / tree_parameters.iterations
            root_weight = tree_parameters.tree_weight_factor * tree_parameters.iterations
            thickness = math.sqrt(1 - section.weight / root_weight)
            light_searching = \
                tree_parameters.light_searching_bottom * (1 - progress) + \
                tree_parameters.light_searching_top * progress + \
                tree_parameters.light_searching_edges * (max(0, thickness-0.97) * 5)
            print(f"progress value: = {thickness} ")


            # Adding the various effects and normalizing.
            direction = direction + \
                light_direction * light_searching * 0.1 + \
                gravity_vector
            direction = direction.normalized()

            # Avoiding ground means that all negative Z values of direction are mitigated.
            direction.z = avoid_ground(direction.z, tree_parameters.ground_avoiding)
            return direction.normalized()
            
        def avoid_ground(value, parameter):
            
            # Cubic function that maps -1 to 0 and 1 to 1
            def cubic_function(x):
                return (x + 1) ** 3 / 8

            # Interpolate between the original value and the cubic function result based on the parameter
            return value * (1 - parameter) + max(cubic_function(value),value) * parameter  
        
        def uniform_random_direction():
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            
            x = math.sin(phi) * math.cos(theta)
            y = math.sin(phi) * math.sin(theta)
            z = math.cos(phi)
            
            return Vector((x, y, z)).normalized()
        
        def create_circle_verts(position, direction, radius, resolution):
            circle_verts = []

            rotation = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()

            for i in range(resolution):
                angle = (2 * math.pi / resolution) * i
                x = position.x + radius * math.cos(angle)
                y = position.y + radius * math.sin(angle)
                z = position.z

                vertex = Vector((x, y, z))
                vertex = rotation @ (vertex - position) + position
                circle_verts.append(vertex)

            return circle_verts

        def create_section_mesh(section, tree_parameters):
            initial_weight = tree_parameters.tree_weight_factor * tree_parameters.iterations
            if section.parent is None:
                radius = tree_parameters.radius
                parent_radius = radius
            else:
                radius = math.sqrt(section.weight / initial_weight) * tree_parameters.radius
                parent_radius = math.sqrt(section.parent.weight / initial_weight) * tree_parameters.radius

            mesh = bpy.data.meshes.new("Branch")
            bm = bmesh.new()

            previous_circle_verts = None
            bottom_bm_verts = None
            bottom_bm_edges = None
            
            for i in range(len(section.points)):
                current_point = section.points[i]
                direction = Vector((0,0,1))
                if i > 1: 
                    prev_point = section.points[i - 1]
                    direction = (current_point - prev_point).normalized()

                # Calculate the lerp factor based on the current index in the section points
                lerp_factor = i / (len(section.points) - 1)
                lerp_factor = math.sqrt(lerp_factor)

                # If the section has a parent, modify the direction and radius
                lerped_radius = radius
                if section.parent:
                    parent_end_direction = (section.parent.points[-1] - section.parent.points[-2]).normalized()
                    direction = direction.lerp(parent_end_direction, 1-lerp_factor)
                    lerped_radius = (parent_radius * (1 - lerp_factor)) + (radius * (lerp_factor))

                current_circle_verts = create_circle_verts(
                    current_point, direction, lerped_radius, tree_parameters.branch_resolution
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
            weight=tree_parameters.tree_weight_factor * tree_parameters.iterations, \
            depth=1,\
            length=1)
        sections = [root_section]

        for iteration_number in range(tree_parameters.iterations):
            grow_step(sections, tree_parameters, iteration_number)
            new_sections = check_splits(sections, tree_parameters, iteration_number)
            sections.extend(new_sections)

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
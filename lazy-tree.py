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
from mathutils import Vector, Quaternion


class Section:
    def __init__(self, points, depth, weight, open_end=True):
        self.points = points
        self.open_end = open_end
        self.depth = depth
        self.weight = weight
        
            

def update_tree():
    bpy.ops.growtree.create_tree()

# Blender classes:        
class GROWTREE_PG_tree_parameters(bpy.types.PropertyGroup):
    seed: bpy.props.IntProperty(name="Seed", default=0, update=update_tree)
    iterations: bpy.props.IntProperty(name="Iterations", default=20, min=0, max=256, update=update_tree)
    split_chance: bpy.props.FloatProperty(name="Split Chance", default=0.05, min=0, max=1, update=update_tree)
    split_angle: bpy.props.FloatProperty(name="Split Angle", default=45, min=0, max=90, update=update_tree)
    light_source: bpy.props.FloatVectorProperty(name="Light Source", default=(0, 0, 1000), update=update_tree)
    light_searching: bpy.props.FloatProperty(name="Light Searching", default=0.5, min=-1, max=2, update=update_tree)
    ground_avoiding: bpy.props.FloatProperty(name="Ground Avoiding", default=0.5, min=-1, max=2, update=update_tree)
    trunk_gravity: bpy.props.FloatProperty(name="Trunk Gravity", default=0.5, min=-1, max=2, update=update_tree)
    split_ratio_bottom: bpy.props.FloatProperty(name="Branch Split Ratio Bottom", default=0.4, min=0.01, max=0.5, update=update_tree)
    split_ratio_top: bpy.props.FloatProperty(name="Branch Split Ratio Top", default=0.1, min=0.01, max=0.5, update=update_tree)



class GROWTREE_OT_create_tree(bpy.types.Operator):
    bl_idname = "growtree.create_tree"
    bl_label = "Create Tree"
    bl_options = {'REGISTER', 'UNDO'}

    tree_parameters: bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)

    def execute(self, context):
        tree_parameters = context.scene.tree_parameters
                        
        # Before calculating a new tree, making sure that the amount of segments isn't 
        # likely to exceed a certain amount. let's say 10000.
        max_segments = 10000 
        est_segments = pow(1 + tree_parameters.split_chance, tree_parameters.iterations)
        if  est_segments > max_segments:
            self.report({'WARNING'}, \
                f"Estimated number of segments ({int(est_segments)}) exceeds the limit ({max_segments}). Aborting.")
            return {'CANCELLED'}
        
        mesh = self.create_tree_mesh(tree_parameters)
        obj_name = "Created Tree"
        
        if obj_name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)

        obj = bpy.data.objects.new(obj_name, mesh)
        bpy.context.collection.objects.link(obj)

        return {'FINISHED'}
    

    def create_tree_mesh(self, tree_parameters):
        
        random.seed(tree_parameters.seed)
    
        def get_random_value(seed):
            random.seed(seed)
            return random.random()
        
        def get_direction(previous_point1, previous_point2):
            direction = (previous_point1 - previous_point2).normalized()
            random_direction = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
            final_direction = (direction + random_direction * 0.05).normalized()*-0.1
            return final_direction

        def grow_step(sections):
            for section in sections:
                if section.open_end:
                    last_point = section.points[-1]
                    quasi_last_point = section.points[-2]
                    new_point = last_point + get_direction(quasi_last_point, last_point)
                    section.points.append(new_point)

        def check_splits(sections, tree_parameters, iteration_number):
            new_sections = []
            for section in sections:
                if section.open_end and random.random() < tree_parameters.split_chance:

                    # A split is happening: the current section is not open-ended anymore.
                    section.open_end = False

                    # Direction is provided by the last segment in the section. Sections start with
                    # two points so we can assume that there are at least 2 points here.
                    initial_direction = get_direction(section.points[-2], section.points[-1])

                    # Calculating the weight of the two branches. The distribution goes from 0 to
                    # 0.5 (equal split). the new branch is always the smaller one.
                    progress = iteration_number / tree_parameters.iterations
                    triangular_peak = \
                        tree_parameters.split_ratio_bottom * (1 - progress) + \
                        tree_parameters.split_ratio_top * progress
                    split_ratio = random.triangular(0., 0.5, triangular_peak)

                    new_section1 = Section( \
                        points=section.points[-1:], \
                        depth=section.depth + 1, \
                        weight=section.weight * (1 - split_ratio), \
                        open_end=True)
                    new_section2 = Section( \
                        points=section.points[-1:], \
                        depth=section.depth + 1, \
                        weight=section.weight * (split_ratio), \
                        open_end=True)

                    # Section A is the main section and tends to follow the previous branch. 
                    # We then generate two random directions for the branches. how much that affects the 
                    # final direction is based on the weight.
                    direction1 = initial_direction.copy()
                    direction2 = initial_direction.copy()
                    random_direction = get_random_direction(tree_parameters)
                    #direction1 = direction1 * new_section1.weight
                    #direction1 = (direction1 + random_direction * new_section2.weight).normalized()
                    angle1 = -tree_parameters.split_angle * split_ratio
                    angle2 = tree_parameters.split_angle * (1 - split_ratio)
                    direction1.rotate(Quaternion(direction1.cross(random_direction).normalized(), math.radians(angle1)))
                    direction2.rotate(Quaternion(direction2.cross(random_direction).normalized(), math.radians(angle2)))

                    new_section1.points.extend([new_section1.points[-1] + direction1])
                    new_section2.points.extend([new_section2.points[-1] + direction2])

                    new_sections.extend([new_section1, new_section2])

            return new_sections

        def get_random_direction(tree_parameters):
            
            # Random direction is calculated in theta-phi to get a more uniform distribution.
            random_direction = uniform_random_direction()

            # Combining the random direction with the light direction
            light_direction = Vector((tree_parameters.light_source[0], tree_parameters.light_source[1], tree_parameters.light_source[2])).normalized()
            
            # Adding the various effects and normalizing.
            random_direction = random_direction + \
                light_direction * tree_parameters.light_searching
            random_direction = random_direction.normalized()

            # Avoiding ground means that all negative Z values of direction are mitigated.
            random_direction.z = avoid_ground(random_direction.z, tree_parameters.ground_avoiding)
            return random_direction.normalized()
            

        def avoid_ground(value, parameter):

            # Quadratic logic. If parameter is < 1 the effect is mostly
            # on the negative elements.
            a = 1 - parameter
            b = parameter * parameter

            if value < 0:
                return a * value + b * value * value
            else:
                return value + b * value * value


        def uniform_random_direction():
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            
            x = math.sin(phi) * math.cos(theta)
            y = math.sin(phi) * math.sin(theta)
            z = math.cos(phi)
            
            return Vector((x, y, z)).normalized()


        mesh = bpy.data.meshes.new("Tree")
        bm = bmesh.new()

        root_section = Section( \
            points=[Vector((0, 0, 0)),Vector((0, 0, 0.1))], \
            weight=tree_parameters.iterations, \
            depth=1)
        sections = [root_section]

        for iteration_number in range(tree_parameters.iterations):
            grow_step(sections)
            new_sections = check_splits(sections, tree_parameters, iteration_number)
            sections.extend(new_sections)

        for section in sections:
            v0 = bm.verts.new(section.points[0])
            for i in range(len(section.points) - 1):
                v1 = bm.verts.new(section.points[i + 1])
                bm.edges.new([v0, v1])
                v0 = v1

        bm.to_mesh(mesh)
        bm.free()

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
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
        
# Blender classes:        
class GROWTREE_PG_tree_parameters(bpy.types.PropertyGroup):
    seed: bpy.props.IntProperty(name="Seed", default=0)
    iterations: bpy.props.IntProperty(name="Iterations", default=20, min=0, max=256)
    split_chance: bpy.props.FloatProperty(name="Split Chance", default=0.05, min=0, max=1)
    split_angle: bpy.props.FloatProperty(name="Split Angle", default=45, min=0, max=90)
    light_source: bpy.props.FloatVectorProperty(name="Light Source", default=(0, 0, 1000))
    light_searching: bpy.props.FloatProperty(name="Light Searching", default=0.5, min=-1, max=2)
    trunk_gravity: bpy.props.FloatProperty(name="Trunk Gravity", default=0.5, min=-1, max=2)
    split_ratio_bottom: bpy.props.FloatProperty(name="Branch Split Ratio Bottom", default=0.4, min=0.01, max=0.5)
    split_ratio_top: bpy.props.FloatProperty(name="Branch Split Ratio Top", default=0.1, min=0.01, max=0.5)


class GROWTREE_OT_create_tree(bpy.types.Operator):
    bl_idname = "growtree.create_tree"
    bl_label = "Create Tree"
    bl_options = {'REGISTER', 'UNDO'}

    tree_parameters: bpy.props.PointerProperty(type=GROWTREE_PG_tree_parameters)

    def execute(self, context):
        tree_parameters = context.scene.tree_parameters
        
        mesh = self.create_tree_mesh(tree_parameters)
        obj_name = "Created Tree"
        
        if obj_name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)

        obj = bpy.data.objects.new(obj_name, mesh)
        bpy.context.collection.objects.link(obj)

        return {'FINISHED'}

    def create_tree_mesh(self, tree_parameters):

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
                    direction = get_direction(section.points[-2], section.points[-1])
                    
                    # The split direction is with a given angle against the product of the 
                    # original direction with a random one.
                    split_direction = direction.copy()
                    random_direction = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
                    light_direction = Vector((tree_parameters.light_source[0], tree_parameters.light_source[1], tree_parameters.light_source[2])).normalized()
                    
                    # Combining the random direction with the light direction.
                    random_direction = (random_direction * (1 - tree_parameters.light_searching) + light_direction * tree_parameters.light_searching).normalized()
                    
                    # Rotating the split branch direction
                    split_direction.rotate(Quaternion(direction.cross(random_direction).normalized(), math.radians(tree_parameters.split_angle)))

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

                    new_section1.points.extend([new_section1.points[-1] + direction])
                    new_section2.points.extend([new_section2.points[-1] + split_direction])

                    new_sections.extend([new_section1, new_section2])

            return new_sections

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
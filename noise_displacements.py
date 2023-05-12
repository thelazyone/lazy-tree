import math
from mathutils import Vector, noise

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
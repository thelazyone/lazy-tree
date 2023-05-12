class Section:
    def __init__(self, points, depth, distance, weight, open_end=True, parent=None, parent_id=None, is_root=False):
        self.points = points
        self.open_end = open_end
        self.depth = depth
        self.distance = distance
        self.weight = weight
        self.parent = parent
        self.parent_id = parent_id
        self.is_root = is_root
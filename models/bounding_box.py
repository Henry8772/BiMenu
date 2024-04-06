
from enum import Enum
from PIL import Image, ImageDraw, ImageFont


class FeatureType(Enum):
    PAGE = 1
    BLOCK = 2
    PARA = 3
    WORD = 4
    SYMBOL = 5


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"(x={self.x}, y={self.y})"


class BoundingBox:
    def __init__(self, vertices, text):
        if all(isinstance(v, Point) for v in vertices):
            self.vertices = vertices
        else:
            # Assume vertices is a list of dictionaries with 'x' and 'y' keys
            self.vertices = [Point(v.get('x', 0), v.get('y', 0)) for v in vertices]
        
        self.text = text

        self.x_min = min(point.x for point in self.vertices)
        self.x_max = max(point.x for point in self.vertices)
        self.y_min = min(point.y for point in self.vertices)
        self.y_max = max(point.y for point in self.vertices)
    
    def get_min_max(self):
        return self.x_min, self.x_max, self.y_min, self.y_max

    def is_overlapping(self, other):
        return not (self.x_max < other.x_min or
                    self.x_min > other.x_max or
                    self.y_max < other.y_min or
                    self.y_min > other.y_max)

    def merge(self, other):
        x_min = min(self.x_min, other.x_min)
        x_max = max(self.x_max, other.x_max)
        y_min = min(self.y_min, other.y_min)
        y_max = max(self.y_max, other.y_max)

        self.text +=  other.text

        self.vertices = [
            Point(x_min, y_min),
            Point(x_max, y_min),
            Point(x_max, y_max),
            Point(x_min, y_max),
        ]
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def get_top_left(self) -> Point:
        return Point(self.x_min, self.y_min)
    
    def get_bottom_right(self) -> Point:
        return Point(self.x_max, self.y_max)

    @staticmethod
    def compute_edge_distance(vertex, edge):
        A, B = edge
        AB = Point(B.x - A.x, B.y - A.y)
        AV = Point(vertex.x - A.x, vertex.y - A.y)
        t = (AV.x * AB.x + AV.y * AB.y) / (AB.x * AB.x + AB.y * AB.y)
        if t <= 0:
            return ((vertex.x - A.x) ** 2 + (vertex.y - A.y) ** 2) ** 0.5
        elif t >= 1:
            return ((vertex.x - B.x) ** 2 + (vertex.y - B.y) ** 2) ** 0.5
        else:
            closest = Point(A.x + t * AB.x, A.y + t * AB.y)
            return ((vertex.x - closest.x) ** 2 + (vertex.y - closest.y) ** 2) ** 0.5

    def compute_distance_to(self, other_bbox):
        min_distance = float('inf')
        edges1 = [(self.vertices[i], self.vertices[(i + 1) % 4]) for i in range(4)]
        edges2 = [(other_bbox.vertices[i], other_bbox.vertices[(i + 1) % 4]) for i in range(4)]

        for v in self.vertices:
            for e in edges2:
                min_distance = min(min_distance, BoundingBox.compute_edge_distance(v, e))

        for v in other_bbox.vertices:
            for e in edges1:
                min_distance = min(min_distance, BoundingBox.compute_edge_distance(v, e))

        return min_distance

    def distance_to(self, other_bbox):
        return self.compute_distance_to(other_bbox)

    def is_close_enough(self, other_bbox, distance):
        return self.compute_distance_to(other_bbox) < distance

    def is_close_enough_vertical(self, other_bbox, distance):
        return self.vertical_distance_to(other_bbox) < distance

    def is_close_enough_horizontal(self, other_bbox, distance):
        return self.horizontal_distance_to(other_bbox) < distance

    def is_between_horizontal(self, box1, box2):
        return (box1.right < self.left < box2.left) or (box2.right < self.left < box1.left)

    def is_between_vertical(self, box1, box2):
        return (box1.bottom < self.top < box2.top) or (box2.bottom < self.top < box1.top)

    def horizontal_distance_to(self, other_bbox):
        return abs(self.left - other_bbox.right) if self.left > other_bbox.right else abs(other_bbox.left - self.right)

    def vertical_distance_to(self, other_bbox):
        return abs(self.top - other_bbox.bottom) if self.top > other_bbox.bottom else abs(other_bbox.top - self.bottom)


class DSU:
    def __init__(self, n):
        self.parent = [i for i in range(n)]
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rootX = self.find(x)
        rootY = self.find(y)
        
        if rootX != rootY:
            if self.rank[rootX] > self.rank[rootY]:
                self.parent[rootY] = rootX
            else:
                self.parent[rootX] = rootY
                if self.rank[rootX] == self.rank[rootY]:
                    self.rank[rootY] += 1
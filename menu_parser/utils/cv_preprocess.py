import io
# from google.cloud import vision
import json
from copy import deepcopy
from PIL import Image, ImageDraw, ImageFont
from models.bounding_box import FeatureType, Point, BoundingBox, DSU

from enum import Enum

class ExtendDirection(Enum):
    LEFT = 'left'
    TOP = 'top'
    RIGHT = 'right'
    BOTTOM = 'bottom'


def process_bounds_in_paragraph(document):
    bounds = []
    for page in document['pages']:
        for block in page['blocks']:
            for paragraph in block['paragraphs']:
                temp_bbox = None
                for word in paragraph['words']:
                    symbols_data = [symbol['text'] for symbol in word['symbols'] if symbol['confidence'] > 0.8]
                    symbols_text = ''.join(symbols_data)

                    if symbols_text:
                        if 'y' not in word['boundingBox']['vertices'][0]:
                            break

                        if temp_bbox:
                            temp_bbox.merge(BoundingBox(word['boundingBox']['vertices'], [symbols_text]))
                        else:
                            temp_bbox = BoundingBox(word['boundingBox']['vertices'], [symbols_text])

                if temp_bbox:
                    bounds.append(temp_bbox)
    return bounds



def group_extended_boxes(extended_boxes, sorted_bounding_boxes):
    grouped_list = []
    grouped_box = []
    for extended_box in extended_boxes:
        current_list = []
        temp_bbox = None
        for bounding_box in sorted_bounding_boxes:
            overlap_area = calculate_overlap_area(extended_box, bounding_box)
            if overlap_area >= 0.5 * ((bounding_box.x_max - bounding_box.x_min) * (bounding_box.y_max - bounding_box.y_min)):
                current_list.append(bounding_box.text)
                if temp_bbox:
                    temp_bbox.merge(bounding_box)
                else:
                    temp_bbox = BoundingBox(bounding_box.vertices,  [bounding_box.text])
        if current_list:
            grouped_list.append(current_list)
            grouped_box.append(temp_bbox)
    return grouped_list, grouped_box


def extend_bounding_boxes(bounding_boxes, container_width, container_height, extend_directions=[ExtendDirection.BOTTOM, ExtendDirection.RIGHT]):
    # Sort bounding boxes by their top-left corner (y_min, then x_min)
    sorted_bounding_boxes = sorted(deepcopy(bounding_boxes), key=lambda bbox: (bbox.y_min, bbox.x_min))

    for direction in extend_directions:

        for i, box in enumerate(sorted_bounding_boxes):
            x_min, x_max, y_min, y_max = box.x_min, box.x_max, box.y_min, box.y_max

            if ExtendDirection.LEFT == direction:
                # Extend to the left
                left_candidates = [b.x_max + 160 for j, b in enumerate(sorted_bounding_boxes) if j != i and b.y_min <= y_max and b.y_max >= y_min and x_min > b.x_max]
                new_x_min = max(left_candidates + [30])
                print(left_candidates)
                x_min = new_x_min

            if ExtendDirection.TOP == direction:
                # Extend upwards
                top_candidates = [b.y_max for j, b in enumerate(sorted_bounding_boxes) if j != i and b.x_min <= x_max and b.x_max >= x_min and y_min > b.y_max]
                new_y_min = max(top_candidates + [0])
                y_min = new_y_min

            if ExtendDirection.RIGHT == direction:
                # Extend to the right
                right_candidates = [b.x_min for j, b in enumerate(sorted_bounding_boxes) if j != i and b.y_min <= y_max and b.y_max >= y_min and x_max < b.x_min]
                new_x_max = min(right_candidates + [container_width]) if right_candidates else container_width
                x_max = new_x_max

            if ExtendDirection.BOTTOM == direction:
                # Extend downwards
                bottom_candidates = [b.y_min-10 for j, b in enumerate(sorted_bounding_boxes) if j != i and b.x_min <= x_max and b.x_max >= x_min and y_max < b.y_min]
                new_y_max = min(bottom_candidates + [container_height]) if bottom_candidates else container_height
                y_max = new_y_max

            # Update the bounding box
            box.x_min, box.x_max, box.y_min, box.y_max = x_min, x_max, y_min, y_max

    return sorted_bounding_boxes


# def extend_bounding_boxes(bounding_boxes, container_width, container_height):
#     # Sort bounding boxes by their top-left corner (y_min, then x_min)
#     sorted_bounding_boxes = sorted(deepcopy(bounding_boxes), key=lambda bbox: (bbox.y_min, bbox.x_min))

#     for i, box in enumerate(sorted_bounding_boxes):
#         x_min, x_max, y_min, y_max = box.x_min, box.x_max, box.y_min, box.y_max

#         right_candidates = [b.x_min for j, b in enumerate(sorted_bounding_boxes) if j != i and b.y_min <= y_max and b.y_max >= y_min and x_max < b.x_min]

#         for j, b in enumerate(sorted_bounding_boxes):
#             if j != i and b.y_min <= y_max and b.y_max >= y_min and x_max < b.x_min:
#                 print(b.text)
#         new_x_max = min(right_candidates + [container_width]) if right_candidates else container_width

#         x_max = new_x_max

#         # Candidates for extension downwards (boxes below and within the horizontal range of the current box)
#         bottom_candidates = [b.y_min for j, b in enumerate(sorted_bounding_boxes) if j != i and b.x_min <= x_max and b.x_max >= x_min and y_max < b.y_min]

        
#         new_y_max = min(bottom_candidates + [container_height]) if bottom_candidates else container_height

#         # Update the bounding box
#         box.x_max, box.y_max = new_x_max, new_y_max

#     return sorted_bounding_boxes


def calculate_overlap_area(box1, box2):
    # Determine the (x, y) coordinates of the intersection rectangle
    x_left = max(box1.x_min, box2.x_min)
    y_top = max(box1.y_min, box2.y_min)
    x_right = min(box1.x_max, box2.x_max)
    y_bottom = min(box1.y_max, box2.y_max)

    # Check if there is no overlap
    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # Calculate the area of overlap
    return (x_right - x_left) * (y_bottom - y_top)

def draw_boxes(image, bounds, color):
    """Draws a border around the image using the hints in the vector list.

    Args:
        image: the input image object.
        bounds: list of coordinates for the boxes.
        color: the color of the box.

    Returns:
        An image with colored bounds added.
    """
    draw = ImageDraw.Draw(image)

    for bound in bounds:
        draw.polygon(
            [
                bound.vertices[0].x,
                bound.vertices[0].y,
                bound.vertices[1].x,
                bound.vertices[1].y,
                bound.vertices[2].x,
                bound.vertices[2].y,
                bound.vertices[3].x,
                bound.vertices[3].y,
                # bound.vertices[0].get('x', 0),
                # bound.vertices[0].get('y', 0),
                # bound.vertices[1].get('x', 0),
                # bound.vertices[1].get('y', 0),
                # bound.vertices[2].get('x', 0),
                # bound.vertices[2].get('y', 0),
                # bound.vertices[3].get('x', 0),
                # bound.vertices[3].get('y', 0),
            ],
            None,
            color,
        )
    return image

def draw_boxes_2_points(image, bounds, outer_color):
    """
    Draws semi-transparent filled boxes with an opaque border around the image using the provided bounding boxes.

    Args:
        image: the input image object.
        bounds: list of bounding boxes, each represented with attributes x_min, x_max, y_min, y_max.
        color: the RGB color of the box border. The fill will be the same color with reduced opacity.

    Returns:
        An image with colored bounds added.
    """
    draw = ImageDraw.Draw(image, 'RGBA')  # Ensure 'RGBA' mode for transparency

    for bound in bounds:
        # Access the coordinates of the four corners of the bounding box
        x_min, x_max, y_min, y_max = bound.x_min, bound.x_max, bound.y_min, bound.y_max
        corners = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]



        # Draw the bounding box with the semi-transparent fill and opaque border
        draw.polygon(corners, outline=outer_color, width=2)

    return image






def group_bounding_boxes(bounding_boxes, vertical_distance, horizontal_distance):
    n = len(bounding_boxes)
    dsu = DSU(n)
    
    for i in range(n):
        for j in range(i+1, n):
            if bounding_boxes[i].is_close_enough(bounding_boxes[j], vertical_distance):
                dsu.union(i, j)
            # elif bounding_boxes[i].is_close_enough_horizontal(bounding_boxes[j], horizontal_distance):
            #     dsu.union(i, j)

    groups = {}
    for i in range(n):
        root = dsu.find(i)
        if root not in groups:
            groups[root] = [bounding_boxes[i]]
        else:
            groups[root].append(bounding_boxes[i])

    # We're returning lists of bounding boxes for each group without merging
    return list(groups.values())

def merge_box_groups(groups):
    merged_boxes = []

    for group in groups:
        merged_box = group[0]
        for box in group[1:]:
            merged_box.merge(box)
        merged_boxes.append(merged_box)

    return merged_boxes

def merge_bbox_list(bbox_list):
    merged_box = bbox_list[0]
    for box in bbox_list[1:]:
        merged_box.merge(box)

    return merged_box




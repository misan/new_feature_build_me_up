import sys
import math
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from collections import namedtuple

from romans_font import Romans

from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import nearest_points
import numpy as np


def most_inland_point(polygon_points, step=0.1):
    polygon = Polygon(polygon_points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty:
        return (0, 0), 0
    inland_point = polygon.representative_point()
    try:
        nearest = nearest_points(inland_point, polygon.boundary)[1]
        radius = inland_point.distance(nearest)
    except (IndexError, ValueError):
        radius = 0
    return (inland_point.x, inland_point.y), radius * 2

def get_polygon_bbox(points):
    if not points:
        return 0, 0, 0, 0
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    return min_x, min_y, max_x, max_y

def parse_problem_file(file_path):
    original_pieces_data = {}
    with open(file_path, 'r') as f:
        lines = f.readlines()
    BinDimension = namedtuple('BinDimension', ['width', 'height'])
    bin_width, bin_height = map(float, lines[0].strip().split())
    bin_dimension = BinDimension(width=bin_width, height=bin_height)
    piece_id_counter = 1
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        points_str = line.split(' ')
        vertices = []
        for point_str in points_str:
            try:
                x_str, y_str = point_str.split(',')
                vertices.append((float(x_str), float(y_str)))
            except ValueError:
                continue
        if vertices:
            min_x, min_y, max_x, max_y = get_polygon_bbox(vertices)
            # Per user instruction, the reference point for rotation is the bottom-left of the original bbox.
            pivot_x = min_x
            pivot_y = min_y
            original_pieces_data[piece_id_counter] = (vertices, (pivot_x, pivot_y))
            piece_id_counter += 1
    return bin_dimension, original_pieces_data

def parse_posiciones_file(file_path):
    bins_data = []
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    line_idx = 0
    bin_count = 1
    while line_idx < len(lines):
        try:
            num_pieces = int(lines[line_idx])
            line_idx += 1
            placed_pieces = []
            for i in range(num_pieces):
                if line_idx >= len(lines):
                    break
                parts = lines[line_idx].split()
                if len(parts) < 4:
                    line_idx += 1
                    continue
                piece_id = int(parts[0])
                rotation = float(parts[1])
                x = float(parts[2])
                y = float(parts[3])
                placed_pieces.append({'id': piece_id, 'rotation': rotation, 'x': x, 'y': y})
                line_idx += 1
            if placed_pieces:
                bins_data.append({'number': bin_count, 'placed_pieces': placed_pieces})
                bin_count += 1
        except ValueError:
            line_idx += 1
    return bins_data

def rotate_point(point, angle_degrees, center):
    angle_rad = math.radians(angle_degrees)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    x, y = point
    cx, cy = center
    new_x = cos_theta * (x - cx) - sin_theta * (y - cy) + cx
    new_y = sin_theta * (x - cx) + cos_theta * (y - cy) + cy
    return new_x, new_y

def create_packing_visual_pdf(bins_data, bin_dimension, original_pieces_data, file_name="output.pdf"):
    c = canvas.Canvas(file_name, pagesize=(bin_dimension.width, bin_dimension.height))
    font = Romans()
    pastel_colors = [colors.Color(0.95, 0.76, 0.76, alpha=0.7), colors.Color(0.76, 0.95, 0.76, alpha=0.7), colors.Color(0.76, 0.76, 0.95, alpha=0.7), colors.Color(0.95, 0.95, 0.76, alpha=0.7), colors.Color(0.95, 0.76, 0.95, alpha=0.7), colors.Color(0.76, 0.95, 0.95, alpha=0.7)]
    for bin_info in bins_data:
        c.setPageSize((bin_dimension.width, bin_dimension.height))
        c.setStrokeColor(colors.blue)
        c.rect(0, 0, bin_dimension.width, bin_dimension.height)
        for piece_info in bin_info['placed_pieces']:
            piece_id = piece_info['id']
            if piece_id not in original_pieces_data:
                continue
            
            original_vertices, rotation_pivot = original_pieces_data[piece_id] # pivot is original min_x, min_y
            rotation_angle = piece_info['rotation']

            # 1. Rotate the shape around its original bottom-left corner (the pivot)
            rotated_vertices = [rotate_point(p, rotation_angle, rotation_pivot) for p in original_vertices]

            # 2. Get the bounding box of the *rotated* shape
            rotated_min_x, rotated_min_y, _, _ = get_polygon_bbox(rotated_vertices)
            
            # 3. Get the final placement coordinates from the file
            final_placed_x = piece_info['x']
            final_placed_y = piece_info['y']

            # 4. Calculate the translation needed to move the rotated shape's bbox-min to the final placement coords
            translation_x = final_placed_x - rotated_min_x
            translation_y = final_placed_y - rotated_min_y
            
            # 5. Apply the final translation
            final_vertices = [(p[0] + translation_x, p[1] + translation_y) for p in rotated_vertices]

            p = c.beginPath()
            p.moveTo(final_vertices[0][0], final_vertices[0][1])
            for point in final_vertices[1:]:
                p.lineTo(point[0], point[1])
            p.close()
            c.setFillColor(random.choice(pastel_colors))
            c.setStrokeColor(colors.blue)
            c.setLineWidth(0.5)
            c.drawPath(p, fill=1, stroke=1)
            final_centroid, size = most_inland_point(final_vertices, 10)
            c.setFillColor(colors.red)
            text = str(piece_id)
            font.scale = size / 80
            text_width = font.get_string_length(text)
            paths = font.get_string(text)
            c.setStrokeColor(colors.red)
            c.setLineWidth(1)
            x_offset = final_centroid[0] - text_width / 2
            y_offset = final_centroid[1] - 10 * font.scale
            for path in paths:
                path_obj = c.beginPath()
                path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset)
                for point in path[1:]:
                    path_obj.lineTo(point[0] + x_offset, point[1] + y_offset)
                c.drawPath(path_obj)
        c.showPage()
    c.save()

def main():
    if len(sys.argv) < 3:
        print("Usage: python visual_vector3.py <shapes_file> <positions_file>")
        sys.exit(1)
    shapes_file = sys.argv[1]
    positions_file = sys.argv[2]
    try:
        bin_dimension, original_pieces_data = parse_problem_file(shapes_file)
    except FileNotFoundError:
        print(f"Error: Shapes file not found at '{shapes_file}'")
        sys.exit(1)
    bins_data = parse_posiciones_file(positions_file)
    if not bins_data:
        print(f"Error: No data found in positions file '{positions_file}'")
        sys.exit(1)
    output_filename = "output.pdf"
    create_packing_visual_pdf(bins_data, bin_dimension, original_pieces_data, file_name=output_filename)
    print(f"PDF saved to {output_filename}")

if __name__ == "__main__":
    main()

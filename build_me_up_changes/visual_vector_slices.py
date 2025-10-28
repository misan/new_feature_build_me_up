import sys
import math
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from collections import namedtuple
import os

from romans_font import Romans

from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import nearest_points
import numpy as np


def most_inland_point(polygon_points, step=0.1):
    """Calculates a point inside a polygon that is furthest from its boundary.

    This function uses an iterative negative buffering approach to find a point
    that is deep inside the polygon, which is useful for label placement.
    It repeatedly shrinks the polygon and finds the centroid of the last valid
    (non-empty) polygon.

    Args:
        polygon_points: A list of (x, y) tuples representing the polygon's vertices.
        step: The amount to shrink the polygon at each iteration.

    Returns:
        A tuple containing the (x, y) coordinates of the inland point and a
        calculated radius (twice the distance to the nearest boundary).
    """
    polygon = Polygon(polygon_points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty:
        return (0, 0), 0

    current_polygon = polygon
    last_valid_polygon = polygon

    # Iteratively shrink the polygon until it disappears
    while not current_polygon.is_empty:
        last_valid_polygon = current_polygon
        current_polygon = current_polygon.buffer(-step)
        
        # If the buffer results in multiple disjoint polygons, use the largest one
        if current_polygon.geom_type == 'MultiPolygon':
            if not current_polygon.geoms:
                break
            current_polygon = max(current_polygon.geoms, key=lambda p: p.area)

    # The desired point is the centroid of the last valid polygon
    if last_valid_polygon.geom_type == 'MultiPolygon':
        if not last_valid_polygon.geoms:
            inland_point = polygon.centroid # Fallback to the original centroid
        else:
            largest_poly = max(last_valid_polygon.geoms, key=lambda p: p.area)
            inland_point = largest_poly.centroid
    else:
        inland_point = last_valid_polygon.centroid

    try:
        # Calculate the distance to the nearest boundary for font scaling
        nearest = nearest_points(inland_point, polygon.boundary)[1]
        radius = inland_point.distance(nearest)
    except (IndexError, ValueError):
        radius = 0
        
    return (inland_point.x, inland_point.y), radius * 2

def get_polygon_bbox(points):
    """Calculates the bounding box of a set of points."""
    if not points:
        return 0, 0, 0, 0
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    return min_x, min_y, max_x, max_y

def parse_problem_file(file_path):
    """Parses the shapes file to extract bin dimensions and piece geometries."""
    original_pieces_data = {}
    with open(file_path, 'r') as f:
        lines = f.readlines()
    BinDimension = namedtuple('BinDimension', ['width', 'height'])
    bin_width, bin_height = map(float, lines[0].strip().split())
    bin_dimension = BinDimension(width=bin_width, height=bin_height)
    piece_id_counter = 1
    # Starts from the 3rd line to skip bin dimensions and piece count
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
            # The reference point for rotation is the bottom-left of the original bbox.
            pivot_x = min_x
            pivot_y = min_y
            original_pieces_data[piece_id_counter] = (vertices, (pivot_x, pivot_y))
            piece_id_counter += 1
    return bin_dimension, original_pieces_data

def parse_slices_file(file_path):
    """Parses the slices file to extract the labels for each piece."""
    labels = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                labels.append(line.split(' ')[0])
    return labels

def parse_posiciones_file(file_path):
    """Parses the positions file to get the placement of each piece."""
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
    """Rotates a point counterclockwise by a given angle around a given center."""
    angle_rad = math.radians(angle_degrees)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    x, y = point
    cx, cy = center
    new_x = cos_theta * (x - cx) - sin_theta * (y - cy) + cx
    new_y = sin_theta * (x - cx) + cos_theta * (y - cy) + cy
    return new_x, new_y

def create_packing_visual_pdf(bins_data, bin_dimension, original_pieces_data, labels, file_name="output.pdf"):
    """Creates the PDF visualization of the packed pieces."""
    c = canvas.Canvas(file_name, pagesize=(bin_dimension.width, bin_dimension.height))
    font = Romans()
    # Set a uniform light gray color with 30% transparency for all parts
    fill_color = colors.Color(0.9, 0.9, 0.9, alpha=0.7)
    for bin_info in bins_data:
        c.setPageSize((bin_dimension.width, bin_dimension.height))
        c.setStrokeColor(colors.blue)
        c.rect(0, 0, bin_dimension.width, bin_dimension.height)
        for piece_info in bin_info['placed_pieces']:
            piece_id = piece_info['id']
            if piece_id not in original_pieces_data:
                continue
            
            original_vertices, rotation_pivot = original_pieces_data[piece_id]
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
            c.setFillColor(fill_color)
            c.setStrokeColor(colors.blue)
            c.setLineWidth(0.5)
            c.drawPath(p, fill=1, stroke=1)
            
            # --- Label Rendering Logic ---
            final_centroid, size = most_inland_point(final_vertices, 10);
            c.setLineWidth(1);

            label = labels[piece_id - 1] if 0 <= (piece_id - 1) < len(labels) else str(piece_id);
            main_font_scale = size / 80;
            secondary_font_scale = main_font_scale * 0.5;

            # Case 1: Label ends with ')' (e.g., "16-3-A)")
            if ')' in label:
                label_part = label.replace(')', '');
                parts = label_part.split('-', 1);
                main_text = parts[0];
                secondary_text = parts[1].replace('-', '') if len(parts) > 1 else '';

                # Main part of the label (large, red)
                font.scale = main_font_scale;
                main_width = font.get_string_length(main_text);
                main_paths = font.get_string(main_text);
                
                # Secondary part of the label (smaller, black)
                font.scale = secondary_font_scale;
                secondary_width = font.get_string_length(secondary_text);
                secondary_paths = font.get_string(secondary_text);

                total_width = main_width + secondary_width;
                x_offset = final_centroid[0] - total_width / 2;
                y_offset = final_centroid[1] - 10 * main_font_scale;

                c.setStrokeColor(colors.red);
                font.scale = main_font_scale;
                for path in main_paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset);
                    c.drawPath(path_obj);

                x_offset += main_width;
                # Raise the baseline of the secondary text to the middle of the main text
                y_offset_secondary = y_offset + (50 * main_font_scale) * 0.2 # Adjusted for better vertical alignment

                c.setStrokeColor(colors.black);
                font.scale = secondary_font_scale;
                for path in secondary_paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset_secondary);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset_secondary);
                    c.drawPath(path_obj);

            # Case 2: Label contains '-' but not ')' (e.g., "51-2" or "5-2-A")
            elif '-' in label:
                parts = label.split('-', 1);
                main_text = parts[0];
                secondary_text = parts[1].replace('-', '');

                # Main part of the label (large, red)
                font.scale = main_font_scale;
                main_width = font.get_string_length(main_text);
                main_paths = font.get_string(main_text);

                # Secondary part of the label (smaller, green)
                font.scale = secondary_font_scale;
                secondary_width = font.get_string_length(secondary_text);
                secondary_paths = font.get_string(secondary_text);

                total_width = main_width + secondary_width;
                x_offset = final_centroid[0] - total_width / 2;
                y_offset = final_centroid[1] - 10 * main_font_scale;

                c.setStrokeColor(colors.red);
                font.scale = main_font_scale;
                for path in main_paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset);
                    c.drawPath(path_obj);

                x_offset += main_width;
                c.setStrokeColor(colors.green);
                font.scale = secondary_font_scale;
                for path in secondary_paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset);
                    c.drawPath(path_obj);

            # Case 3: Standard label (no hyphens)
            else:
                c.setStrokeColor(colors.red);
                font.scale = main_font_scale;
                text_width = font.get_string_length(label);
                paths = font.get_string(label);
                x_offset = final_centroid[0] - text_width / 2;
                y_offset = final_centroid[1] - 10 * font.scale;
                for path in paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset);
                    c.drawPath(path_obj);
        c.showPage();
    c.save();

def main():
    """Main function to parse input files and generate the PDF."""
    if len(sys.argv) < 4:
        print("Usage: python visual_vector_slices.py <shapes_file> <positions_file> <slices_file>")
        sys.exit(1)
    shapes_file = sys.argv[1]
    positions_file = sys.argv[2]
    slices_file = sys.argv[3]
    try:
        bin_dimension, original_pieces_data = parse_problem_file(shapes_file)
    except FileNotFoundError:
        print(f"Error: Shapes file not found at '{shapes_file}'")
        sys.exit(1)
    try:
        labels = parse_slices_file(slices_file)
    except FileNotFoundError:
        print(f"Error: Slices file not found at '{slices_file}'")
        sys.exit(1)
    bins_data = parse_posiciones_file(positions_file)
    if not bins_data:
        print(f"Error: No data found in positions file '{positions_file}'")
        sys.exit(1)
    
    # Construct output filename from the shapes file name
    base_name = os.path.splitext(os.path.basename(shapes_file))[0]
    output_filename = f"{base_name}.pdf"
    
    create_packing_visual_pdf(bins_data, bin_dimension, original_pieces_data, labels, file_name=output_filename)
    print(f"PDF saved to {output_filename}")

if __name__ == "__main__":
    main()

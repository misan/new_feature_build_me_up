import sys
import math
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from collections import namedtuple
import os

import io
import zipfile

from romans_font import Romans

from polylabel import polylabel

from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely.ops import nearest_points
import numpy as np




def get_polygon_bbox(points):
    """Calculates the bounding box of a set of points."""
    if not points:
        return 0, 0, 0, 0
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    return min_x, min_y, max_x, max_y

def parse_posiciones_file(f):
    """Parses the positions file from a file-like object."""
    bins_data = []
    lines = [line.strip() for line in f.readlines() if line.strip()]
    
    current_bin_pieces = []
    bin_count = 1

    for line in lines:
        parts = line.split()
        is_header = False
        if len(parts) == 1:
            try:
                int(parts[0])
                is_header = True
            except ValueError:
                is_header = False
        
        if is_header:
            if current_bin_pieces:
                bins_data.append({'number': bin_count, 'placed_pieces': current_bin_pieces})
                bin_count += 1
            current_bin_pieces = []
        else:
            if len(parts) >= 4:
                try:
                    piece_name = parts[0]
                    rotation = float(parts[1])
                    x = float(parts[2])
                    y = float(parts[3])
                    current_bin_pieces.append({'name': piece_name, 'rotation': rotation, 'x': x, 'y': y})
                except ValueError:
                    pass
    
    if current_bin_pieces:
        bins_data.append({'number': bin_count, 'placed_pieces': current_bin_pieces})

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

def parse_and_transform_slices(f):
    """Parses slices.txt from a file-like object, groups by block, flips, and returns transformed data."""
    lines = f.readlines()
    
    first_line = lines[0].strip() if lines else ""
    first_tag = first_line.split(' ')[0] if first_line else "output"

    blocks = {}
    
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        
        name = parts[0]
        try:
            block_id_str = name.split('-')[0]
            block_id = int(block_id_str)
            
            polygon = []
            j = 1
            while j < len(parts) - 1:
                try:
                    x = float(parts[j])
                    y = float(parts[j+1])
                    polygon.append((x, y))
                    j += 2
                except (ValueError, IndexError):
                    j += 1
                    continue
            
            if block_id not in blocks:
                blocks[block_id] = []
            blocks[block_id].append({'name': name, 'poly': polygon})

        except (ValueError, IndexError):
            continue

    transformed_pieces_data = {}
    for block_id, poly_infos in blocks.items():
        x_max = -float('inf')
        for info in poly_infos:
            for x, y in info['poly']:
                if x > x_max:
                    x_max = x
        
        for info in poly_infos:
            name = info['name']
            original_poly = info['poly']
            
            flipped_polygon = [(x_max - x, y) for x, y in original_poly]
            
            min_x, min_y, _, _ = get_polygon_bbox(flipped_polygon)
            pivot = (min_x, min_y)
            
            transformed_pieces_data[name] = (flipped_polygon, pivot, name)

    return transformed_pieces_data, first_tag

    blocks = {}
    
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            
            name = parts[0]
            try:
                block_id_str = name.split('-')[0]
                block_id = int(block_id_str)
                
                polygon = []
                j = 1
                while j < len(parts) - 1:
                    try:
                        x = float(parts[j])
                        y = float(parts[j+1])
                        polygon.append((x, y))
                        j += 2
                    except (ValueError, IndexError):
                        j += 1
                        continue
                
                if block_id not in blocks:
                    blocks[block_id] = []
                blocks[block_id].append({'name': name, 'poly': polygon})

            except (ValueError, IndexError):
                continue

    transformed_pieces_data = {}
    for block_id, poly_infos in blocks.items():
        x_max = -float('inf')
        for info in poly_infos:
            for x, y in info['poly']:
                if x > x_max:
                    x_max = x
        
        for info in poly_infos:
            name = info['name']
            original_poly = info['poly']
            
            flipped_polygon = [(x_max - x, y) for x, y in original_poly]
            
            min_x, min_y, _, _ = get_polygon_bbox(flipped_polygon)
            pivot = (min_x, min_y)
            
            transformed_pieces_data[name] = (flipped_polygon, pivot, name)

    return transformed_pieces_data, first_tag

def create_packing_visual_pdf(bins_data, transformed_pieces_data, file_name="output.pdf"):
    """Creates the PDF visualization of the packed pieces."""
    c = canvas.Canvas(file_name)
    font = Romans()
    fill_color = colors.Color(0.9, 0.9, 0.9, alpha=0.7)

    MARGIN = 10
    BIN_WIDTH = 2000
    BIN_HEIGHT = 1200

    PAGE_WIDTH = BIN_HEIGHT + 2 * MARGIN
    PAGE_HEIGHT = BIN_WIDTH + 2 * MARGIN

    for bin_info in bins_data:
        
        c.setPageSize((PAGE_WIDTH, PAGE_HEIGHT))
        
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(MARGIN, MARGIN, BIN_HEIGHT, BIN_WIDTH)

        pieces_to_draw = []

        for piece_info in bin_info['placed_pieces']:
            piece_name = piece_info['name']
            if piece_name not in transformed_pieces_data:
                continue
            
            original_vertices, rotation_pivot, _ = transformed_pieces_data[piece_name]
            rotation_angle = piece_info['rotation']

            rotated_vertices = [rotate_point(p, rotation_angle, rotation_pivot) for p in original_vertices]
            rotated_min_x, rotated_min_y, _, _ = get_polygon_bbox(rotated_vertices)
            
            final_placed_x = piece_info['x']
            final_placed_y = piece_info['y']

            translation_x = final_placed_x - rotated_min_x
            translation_y = final_placed_y - rotated_min_y
            
            final_vertices = [(p[0] + translation_x, p[1] + translation_y) for p in rotated_vertices]
            
            pieces_to_draw.append({'name': piece_name, 'vertices': final_vertices})

        for piece in pieces_to_draw:
            # Original landscape vertices
            landscape_vertices = piece['vertices']
            
            # Transform vertices to portrait
            page_vertices = [(BIN_HEIGHT - p[1] + MARGIN, p[0] + MARGIN) for p in landscape_vertices]

            p = c.beginPath()
            p.moveTo(page_vertices[0][0], page_vertices[0][1])
            for point in page_vertices[1:]:
                p.lineTo(point[0], point[1])
            p.close()
            c.setFillColor(fill_color)
            c.setStrokeColor(colors.blue)
            c.setLineWidth(0.5)
            c.drawPath(p, fill=1, stroke=1)
            
            # The polygon for label placement is in the landscape coordinate system
            polygon = Polygon(landscape_vertices)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)

            if polygon.is_empty:
                label_point_landscape = Point(0, 0)
                size = 0
            else:
                # Use polylabel to find the best position for the label
                # polylabel expects a list of rings, where each ring is a list of points
                label_coords = polylabel([list(polygon.exterior.coords)])
                label_point_landscape = Point(label_coords)
                distance = label_point_landscape.distance(polygon.boundary)
                size = distance * 2

            # Transform the label point to portrait coordinates
            label_point = Point(BIN_HEIGHT - label_point_landscape.y + MARGIN, label_point_landscape.x + MARGIN)

            c.setLineWidth(1);

            label = piece['name']
            main_font_scale = size / 80;
            secondary_font_scale = main_font_scale * 0.5;

            if ')' in label:
                label_part = label.replace(')', '');
                parts = label_part.split('-', 1);
                main_text = parts[0];
                secondary_text = parts[1].replace('-', '') if len(parts) > 1 else '';

                font.scale = main_font_scale;
                main_width = font.get_string_length(main_text);
                main_paths = font.get_string(main_text);
                
                font.scale = secondary_font_scale;
                secondary_width = font.get_string_length(secondary_text);
                secondary_paths = font.get_string(secondary_text);

                total_width = main_width + secondary_width;
                x_offset = label_point.x - total_width / 2;
                y_offset = label_point.y - 10 * main_font_scale;

                c.setStrokeColor(colors.red);
                font.scale = main_font_scale;
                for path in main_paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset);
                    c.drawPath(path_obj);

                x_offset += main_width;
                y_offset_secondary = y_offset + (50 * main_font_scale) * 0.2

                c.setStrokeColor(colors.black);
                font.scale = secondary_font_scale;
                for path in secondary_paths:
                    path_obj = c.beginPath();
                    path_obj.moveTo(path[0][0] + x_offset, path[0][1] + y_offset_secondary);
                    for point in path[1:]:
                        path_obj.lineTo(point[0] + x_offset, point[1] + y_offset_secondary);
                    c.drawPath(path_obj);

            elif '-' in label:
                parts = label.split('-', 1);
                main_text = parts[0];
                secondary_text = parts[1].replace('-', '');

                font.scale = main_font_scale;
                main_width = font.get_string_length(main_text);
                main_paths = font.get_string(main_text);

                font.scale = secondary_font_scale;
                secondary_width = font.get_string_length(secondary_text);
                secondary_paths = font.get_string(secondary_text);

                total_width = main_width + secondary_width;
                x_offset = label_point.x - total_width / 2;
                y_offset = label_point.y - 10 * main_font_scale;

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

            else:
                c.setStrokeColor(colors.red);
                font.scale = main_font_scale;
                text_width = font.get_string_length(label);
                paths = font.get_string(label);
                x_offset = label_point.x - text_width / 2;
                y_offset = label_point.y - 10 * font.scale;
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
    
    bins_data = None
    transformed_pieces_data = None
    first_tag = "output"

    if len(sys.argv) == 2:
        # Single file argument, assume it's a zip file
        zip_file_path = sys.argv[1]
        if not os.path.exists(zip_file_path):
            print(f"Error: Input file not found at '{zip_file_path}'")
            sys.exit(1)
            
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                slices_content = zip_ref.read('slices.txt').decode('utf-8')
                positions_content = zip_ref.read('positions.txt').decode('utf-8')
                
                with io.StringIO(slices_content) as slices_io, io.StringIO(positions_content) as positions_io:
                    transformed_pieces_data, first_tag = parse_and_transform_slices(slices_io)
                    bins_data = parse_posiciones_file(positions_io)

        except (zipfile.BadZipFile, KeyError) as e:
            print(f"Error processing zip file: {e}")
            sys.exit(1)

    elif len(sys.argv) == 3:
        # Two file arguments
        slices_file_path = sys.argv[1]
        positions_file_path = sys.argv[2]
        try:
            with open(slices_file_path, 'r') as f_slices:
                transformed_pieces_data, first_tag = parse_and_transform_slices(f_slices)
            with open(positions_file_path, 'r') as f_pos:
                bins_data = parse_posiciones_file(f_pos)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python visualize_transformed_slices_v2_portrait.py <zip_file> | <slices_file> <positions_file>")
        sys.exit(1)

    if not bins_data or not transformed_pieces_data:
        print("Error: Failed to parse input files.")
        sys.exit(1)

    output_filename = f"{first_tag.split('-')[0]}_v2_portrait.pdf"
    
    create_packing_visual_pdf(bins_data, transformed_pieces_data, file_name=output_filename)
    print(f"PDF saved to {output_filename}")

if __name__ == "__main__":
    main()

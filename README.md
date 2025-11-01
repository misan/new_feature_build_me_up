## Introduction
That is a sample of how to create a visualization of the nesting result of a project. It uses three different files to get the result:
1. Shape files contain a list of coordinates; each line represents a closed shape. The first line defines the size of the material sheet, and the second line defines the number of shapes in the file.
2. Posiciones files contain a list of sheets and the parts they contain.
3. Slice files contain the names of each part (and also a list of coordinates, but unfortunately not in an orientation consistent with the nesting, so we will only use the part names, which are the first tag of each line.

## File Formats
**Shapes.txt**  
2000 1200     <-- width and height of material sheets in mm  
1             <-- this file contains just one part  
0,0 0,10.5 10.5,10.5 10.5,0 0,0   <-- coordinates of that part (decimal numbers), this is a 10.5mm square.  

**posiciones.txt**  
1                <-- how many parts follow (only one part for the first sheet in this example)  
1 90 10 20       <-- 1=part_id (1-index), 0=angle_of_rotation, 10=x_offset, 20=y_offset  
3                <-- this indicates a new sheet containing 3 parts  
3 0 50 100       <-- now the three parts of sheet 2, this is the first one  
2 90 412.56 300.5  
4 270 912.25 700.45  
EOF  
As there are no more lines, we know only two sheets were used for this nesting.  
The way we use this information is to position each normalized contour from Shapes.txt into a given sheet of material, at precisely (x_offset,y_offset) after the part has been rotated by the angle_of_rotation. Please note the offset is applied to the (xmin,ymin) corner of the part (we use Cartesian coordinates, where the origin of coordinates is in the bottom-left corner).  


## Sample code
This will read the two types of file above and it will create a set of PNG files showing how the parts are nested on each bin.

```
import os
from data_loader import load_polygons_from_file
from geometry_utils import rotate_polygon, translate_polygon
from visualizer import plot_shapes
from shapely.geometry import Polygon

def load_nesting_solution(shapes_file_path, positions_file_path):
    """
    Loads a nesting solution, including the original shapes and their transformations.

    Args:
        shapes_file_path (str): The absolute path to the Shapes.txt file.
        positions_file_path (str): The absolute path to the posiciones.txt file.

    Returns:
        tuple: A tuple containing (bin_width, bin_height, list_of_bins).
    """
    bin_width, bin_height, original_shapes = load_polygons_from_file(shapes_file_path)
    bins = []
    
    with open(positions_file_path, 'r') as f:
        lines = f.readlines()
        
    current_line_index = 0
    while current_line_index < len(lines):
        line = lines[current_line_index].strip()
        if not line:
            current_line_index += 1
            continue
        
        try:
            num_shapes_in_bin = int(line)
            current_line_index += 1
            
            bin_shapes = []
            for _ in range(num_shapes_in_bin):
                if current_line_index >= len(lines):
                    break
                
                parts = lines[current_line_index].strip().split()
                part_id = int(parts[0]) - 1  # 1-indexed to 0-indexed
                rotation = float(parts[1])
                dx = float(parts[2])
                dy = float(parts[3])
                
                shape_to_place = original_shapes[part_id]
                
                # Rotate the shape first around its centroid
                rotated_shape = rotate_polygon(shape_to_place, rotation, origin='centroid')
                
                # Get the bottom-left corner of the rotated shape's bounding box
                min_x, min_y, _, _ = rotated_shape.bounds
                
                # Calculate the translation needed to move the bottom-left corner to (dx, dy)
                final_dx = dx - min_x
                final_dy = dy - min_y
                
                # Translate to the final position
                placed_shape = translate_polygon(rotated_shape, final_dx, final_dy)
                
                bin_shapes.append(placed_shape)
                current_line_index += 1
            
            bins.append(bin_shapes)
            
        except ValueError:
            # This handles cases where a line is not an integer, which we assume is a data line.
            # The main loop structure should handle this, but as a safeguard:
            current_line_index += 1
            
    return bin_width, bin_height, bins

if __name__ == '__main__':
    base_path = "" # change this to fit the source folder you have your data files
    shapes_file = "015934ca-6d00-4091-8712-378f0d644dca_TigreSerpiente2,5mNC-Shapes.txt"
    positions_file = "015934ca-6d00-4091-8712-378f0d644dca_TigreSerpiente2,5mNC-posiciones.txt"
    
    shapes_file_path = os.path.join(base_path, shapes_file)
    positions_file_path = os.path.join(base_path, positions_file)
    
    bin_width, bin_height, nested_bins = load_nesting_solution(shapes_file_path, positions_file_path)
    
    print(f"Found {len(nested_bins)} bins with dimensions {bin_width}x{bin_height}.")
    bin_polygon = Polygon([(0, 0), (bin_width, 0), (bin_width, bin_height), (0, bin_height)])
    
    for i, bin_shapes in enumerate(nested_bins):
        print(f"  Bin {i+1} has {len(bin_shapes)} shapes.")
        # Visualize each bin
        all_shapes_to_plot = [bin_polygon] + bin_shapes
        plot_shapes(all_shapes_to_plot, output_filename=f"bin_{i+1}_visualization.png")
        print(f"  -> Visualization saved to bin_{i+1}_visualization.png")
```





   

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







   

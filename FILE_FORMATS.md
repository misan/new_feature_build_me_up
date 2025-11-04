
# File Formats

This document describes the format of the text files used in this project.

## `*-Shapes.txt`

This file type defines the original, unprocessed polygon shapes and the dimensions of the material or bin they belong to.

- **Line 1:** Contains two space-separated floating-point numbers representing the `width` and `height` of the bin.
  ```
  2000 1200
  ```

- **Line 2:** Contains a single integer representing the total number of polygons defined in the file.
  ```
  228
  ```

- **Line 3 onwards:** Each subsequent line defines a single polygon.
  - The line consists of space-separated tokens.
  - Each token is a vertex of the polygon, represented by a pair of comma-separated floating-point numbers (`x,y`).

  **Example Polygon Line:**
  ```
  130.56,109.70 130.29,109.63 130.21,109.54 ...
  ```

## `*-slices.txt`

This file type contains the processed polygon "slices".

- Each line in the file represents a single polygon slice.
- **First Token (Identifier):** The first token on each line is a string identifier for that specific slice.
  - The identifier typically follows a format like `block_id-slice_id` (e.g., `23-7`), but can be more complex (e.g., `16-3-A)`).
  - The `block_id` (the integer before the first hyphen) is used to group related slices together for transformations.
- **Subsequent Tokens (Vertices):** The rest of the line is a sequence of space-separated floating-point numbers representing the vertices of the polygon (`x1 y1 x2 y2 ...`).

**Example Slice Line:**
```
23-7 53 4 54 4 55 4 56 5 ...
```

## `posiciones.txt`

This file defines how the polygon slices are placed into different bins, which correspond to the pages in the final output PDF.

- The file is organized into blocks, where each block of lines defines the contents of a single bin.
- **Bin Header Line:** A new bin is declared by a line containing a single integer. This number indicates how many pieces are placed in that bin.
- **Piece Data Lines:** Following a bin header, each line specifies the placement of one piece.
  - **Column 1 (Line Number):** An integer that corresponds to the **1-based line number** of the polygon in the `*-slices.txt` file.
  - **Column 2 (Rotation):** A floating-point number for the rotation angle in degrees.
  - **Column 3 (X-coordinate):** A floating-point number for the final x-coordinate of the piece's placement.
  - **Column 4 (Y-coordinate):** A floating-point number for the final y-coordinate of the piece's placement.

**Example `posiciones.txt` structure:**
```
33
84 270 0 0
145 360 819.423 0
... (31 more piece lines) ...
34
12 360 0 0
116 270 816.506 0
... (32 more piece lines) ...
```

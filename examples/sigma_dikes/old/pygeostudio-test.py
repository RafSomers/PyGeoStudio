from pygeostudio import Study
import pandas as pd

# === Step 1: Load the GeoStudio project ===
study = Study("ZeeSchelde_T4000_No_Clay_25min.gsz")
geom = study.geometry

# === Step 2: Remove point 10 and all lines referencing it ===
point_to_remove = 10
geom.remove_point(point_to_remove)

# Remove lines that reference point 10
lines_to_remove = [line for line in geom.lines if point_to_remove in (line.point1.id, line.point2.id)]
for line in lines_to_remove:
    geom.remove_line(line.id)

# === Step 3: Add a new line connecting point 9 to point 5 ===
new_line_id = max(line.id for line in geom.lines) + 1
geom.add_line(new_line_id, 9, 5)

# === Step 4: Load coordinates from Excel and update points ===
excel_file = "cross_sections_schelde_quantiles 1.xlsx"
df = pd.read_excel(excel_file, header=None)

# Find the row where fid == 0.50
row = df[df[0] == 0.50].values.flatten()

# Extract coordinates correctly: x1, y1, x2, y2, ...
# So we pair (x1, y1), (x2, y2), ...
coords = list(zip(row[2::2], row[1::2]))  # Correct x/y pairing

# Map to point IDs
point_updates = {
    11: coords[0],
    9:  coords[1],
    5:  coords[2],
    7:  coords[3],
    8:  coords[4],
    2:  coords[5],
}

# Update the points
for pid, (x, y) in point_updates.items():
    geom.update_point(pid, x=x, y=y)

# === Step 5: Save the updated model ===
study.save("ZeeSchelde_T4000_No_Clay_25min_updated.gsz")

print("Model updated and saved successfully.")

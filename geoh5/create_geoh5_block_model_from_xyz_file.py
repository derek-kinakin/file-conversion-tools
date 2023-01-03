"""
Convert a regular gridded block model provided as x,y,z coordinates and data to 
GEOH5 format file.

Reads a TOML file with the following block model parameters:
    * Block model name
    * filepath for a CSV file with x,y,z coordinates of block centroids and
      data values for each centroid
    * Names for the coordinate data columns
    * Numeric types for each data values
    * Value maps for each integer value type mapped to a referenced (named)
      value

Outputs a GEOH5 format file to the specified filepath. 

@author: D. Kinakin

Change log:
2023-01-03 Initial version based on Python 3.10

"""

import numpy as np
import pandas as pd
import pyvista as pv
import toml

from pathlib import Path
from geoh5py.workspace import Workspace
from geoh5py.objects import BlockModel


# Globals
TOML_PATH = r"C:\Users\dkinakin\Desktop\example_block_model_parameters.toml"
GEOH5_PATH = r"C:\Users\dkinakin\Desktop\my_block_model.geoh5"


# Functions
def read_xyz_file_to_dataframe(xyzfilepth, xc_name, yc_name, zc_name):
    print("Reading model data from CSV...")
    column_renames = {
        xc_name: "x",
        yc_name: "y",
        zc_name: "z",
    }

    bm = pd.read_csv(xyzfilepth)
    bm = bm.rename(column_renames, axis="columns")
    return bm


def point_set_from_xyz_dataframe(xyzdf, float_val_list, int_val_param_list):
    print("Creating PyVista points from XYZ...")
    points = pv.PointSet(xyzdf[["x", "y", "z"]].to_numpy(dtype=np.float32))

    for p in float_val_list:
        points[p] = xyzdf[p].to_numpy(dtype=np.float32)

    for i in int_val_param_list:
        points[i] = xyzdf[i].to_numpy(dtype=np.int8)
    return points


def extract_block_model_grid_from_xyz_dataframe(xyzdf):
    print("Extracting block model grid configuration...")
    e = xyzdf["x"].unique()
    n = xyzdf["y"].unique()
    z = xyzdf["z"].unique()

    xn = e.shape[0]
    yn = n.shape[0]
    zn = z.shape[0]

    xs = (e.max() - e.min()) / (xn - 1)
    ys = (n.max() - n.min()) / (yn - 1)
    zs = (z.max() - z.min()) / (zn - 1)

    origin = [e.min() - xs / 2, n.min() - ys / 2, z.min() - zs / 2]

    print(f"Block dim X = {xs} for {xn} blocks")
    print(f"Block dim Y = {ys} for {yn} blocks")
    print(f"Block dim Z = {zs} for {zn} blocks")
    print(f"Block model origin {origin} (x, y, z)")
    return xn, yn, zn, xs, ys, zs, origin


# Script #######################################################################
# Covert raw paths
block_model_params_path = Path(TOML_PATH)
geoh5_path = Path(GEOH5_PATH)

# Model parameters
block_model_params = toml.load(block_model_params_path)
block_model_name = block_model_params["setup"]["name"]
block_model_file_path = Path(block_model_params["setup"]["path"])
block_model_x = block_model_params["setup"]["x_coord"]
block_model_y = block_model_params["setup"]["y_coord"]
block_model_z = block_model_params["setup"]["z_coord"]
float_parameters = block_model_params["parameters"]["float_params"]
integer_parameters = block_model_params["parameters"]["integer_params"]
all_value_maps = block_model_params["mapping"]

# Extract data from original block model file
block_model_dataframe = read_xyz_file_to_dataframe(
    block_model_file_path, block_model_x, block_model_y, block_model_z
)
xn, yn, zn, xs, ys, zs, origin = extract_block_model_grid_from_xyz_dataframe(
    block_model_dataframe
)
points = point_set_from_xyz_dataframe(
    block_model_dataframe, float_parameters, integer_parameters
)

# Create geoh5 block model and add data
with Workspace(geoh5_path) as workspace:
    blockmodel = BlockModel.create(
        workspace,
        origin=origin,
        u_cell_delimiters=np.cumsum(
            np.pad(np.ones(xn) * xs, (1, 0), "constant")
        ),  # Offsets along u
        v_cell_delimiters=np.cumsum(
            np.pad(np.ones(yn) * ys, (1, 0), "constant")
        ),  # Offsets along v
        z_cell_delimiters=np.cumsum(
            np.pad(np.ones(zn) * zs, (1, 0), "constant")
        ),  # Offsets along z
        rotation=0.0,
        name=block_model_name,
    )

    # Interpolate data from provided points to block model grid centroids
    print("Interpolating data on to block model grid...")
    bm_xyz_df = pv.PolyData(blockmodel.centroids)
    bm_xyz_df = bm_xyz_df.interpolate(
        points, sharpness=5, n_points=1, strategy="null_value"
    )

    # Add interpolated data to block model grid
    for p in float_parameters:
        print(f"Adding float value {p} to block model...")
        blockmodel.add_data(
            {
                p: {
                    "association": "CELL",
                    "values": bm_xyz_df[p],
                    "entity_type": {"primitive_type": "FLOAT"},
                }
            }
        )

    for i in integer_parameters:
        print(f"Adding integer value {i} to block model...")
        value_map_raw = all_value_maps[i]
        value_map = {int(k): v for k, v in value_map_raw.items()}
        value_map[0] = "Unknown"
        blockmodel.add_data(
            {
                i: {
                    "association": "CELL",
                    "values": bm_xyz_df[i],
                    "entity_type": {
                        "primitive_type": "REFERENCED",
                        "value_map": value_map,
                    },
                }
            }
        )
print("Complete!")

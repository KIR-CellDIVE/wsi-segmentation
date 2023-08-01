
import os
import numpy as np
from deepcell.applications import Mesmer
from pathlib import Path
import gc
from math import ceil

def _xy_ratio(col_tile_size, row_tile_size):
        if 0 in [col_tile_size, row_tile_size]:
            return True
        return(2.0 >= col_tile_size/row_tile_size >= 0.5)

def _xy_ratios(img_col_dim, img_row_dim, col_tile_size, row_tile_size, n, overlap):
    last_col_tile = _last_tile_dim(img_col_dim, col_tile_size, n, overlap)
    last_row_tile = _last_tile_dim(img_row_dim, row_tile_size, n, overlap)
    return(_xy_ratio(col_tile_size, row_tile_size) and _xy_ratio(last_col_tile, row_tile_size) and _xy_ratio(col_tile_size, last_row_tile) and _xy_ratio(last_col_tile, last_row_tile))

def _max_tile_size(col_dim, row_dim, ref=5000*5000):
    return(col_dim*row_dim < ref)

def _smallest_tile_dim(dim_size,n,overlap):
    return(ceil(dim_size/n + overlap - overlap/n))

def _smallest_tile_dim_const(smallest_tile_dim, factor=0.5):
    return(ceil(factor*smallest_tile_dim))

def _smallest_tile_dim_comb(dim_size,n,overlap,factor=0.5):
    smallest_tile_dim = _smallest_tile_dim(dim_size,n,overlap)
    smallest_tile_oppdim = _smallest_tile_dim_const(smallest_tile_dim, factor=factor)
    return(smallest_tile_dim,smallest_tile_oppdim)

def _largest_tile_tile_dim(side,n, overlap):
    return(((3-n) * overlap - side)/(1-n))

def _largest_tile_dim_const(largest_tile_dim, factor=2):
    return(factor*largest_tile_dim)

def _sum_tiles(tile_dim_size, n, overlap):
    return(n*(tile_dim_size-overlap)+overlap)

def _overhang(dim_size, tile_dim_size, n, overlap):
    return(_sum_tiles(tile_dim_size, n, overlap) - dim_size)

def _last_tile_dim(dim_size, tile_dim_size, n, overlap):
    return(tile_dim_size - _overhang(dim_size, tile_dim_size, n, overlap))

def combined_constraints(img_col_dim, img_row_dim, n, overlap):
    # calculate if given n and overlap o what the smallest ci and ri is
    sci = _smallest_tile_dim(img_col_dim, n, overlap)
    sri = _smallest_tile_dim(img_row_dim, n, overlap)

    if (_max_tile_size(sci, sri) == True):
        if _xy_ratios(img_col_dim, img_row_dim, sci, sri, n, overlap) :
            return({'col_tile_size' : sci, 'row_tile_size' : sri, 'n_tiles' : n, 'overlap' : overlap})
        else:
            smallest_row_given_sci = _smallest_tile_dim_const(sci)
            smallest_col_given_sri = _smallest_tile_dim_const(sri)
            
            if sci <= smallest_col_given_sri:
                if _xy_ratios(img_col_dim, img_row_dim, smallest_col_given_sri, sri, n, overlap):
                    return({'col_tile_size' : smallest_col_given_sri, 'row_tile_size' : sri, 'n_tiles' : n, 'overlap' : overlap})
            elif sri <= smallest_row_given_sci:
                if _xy_ratios(img_col_dim, img_row_dim, sci, smallest_row_given_sci, n, overlap):
                    return({'col_tile_size' : sci, 'row_tile_size' : smallest_row_given_sci, 'n_tiles' : n, 'overlap' : overlap})            
        return(None)
    
    else:
        return(None) 

    

def tile_sizer(img_col_dim, img_row_dim, overlap, max_tile_area = 5000*5000, min_tile_area = 500^2, n_tiles = range(2,11)):
    res = None
    
    if _max_tile_size(img_col_dim,img_row_dim) and _xy_ratio(img_col_dim, img_row_dim):
        res = {'col_tile_size' : img_col_dim, 'row_tile_size' : img_row_dim, 'n_tiles' : 1, 'overlap' : 0}
    else:
        for n in n_tiles:
            res = combined_constraints(img_col_dim, img_row_dim, n, overlap)
            if res != None:
                break
    
    if res == None:
         raise ValueError(f"No appropriate tile size for image of size {img_col_dim} x {img_row_dim} and overlap {overlap} could be determined. Consider defining your own tile sizes via `tile_size_row` and `tile_size_col` arguments.")
    else:
        return(res)
    

def remove_boundary_mask(arr, boundary, boundary_sides, dummy_var):
    boundary_ids = list()
    for boundary_side in boundary_sides:
        if "t" in boundary_side:
            boundary_mask = arr[0:boundary, :]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
            
        elif "b" in boundary_side:
            boundary_mask = arr[-boundary:, :]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
            
        elif "r" in boundary_side:
            boundary_mask = arr[:, -boundary:]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]

        elif "l" in boundary_side:
            boundary_mask = arr[:, 0:boundary]
            _boundary_ids = np.unique(boundary_mask)
            boundary_ids = [j for i in [boundary_ids, _boundary_ids] for j in i]
    
    boundary_ids = np.unique(boundary_ids)
    boundary_ids= [i for i in boundary_ids if i != 0]
    cleaned_arr = np.where(np.isin(arr, boundary_ids), dummy_var, arr)
    return(cleaned_arr)
    

def determine_boundaries(img, r0,r1,c0,c1):
    boundaries = list()
    if c0 != 0:
        boundaries.append("l")
    if c1 != img.shape[2]:
        boundaries.append("r")
    if r0 != 0:
        boundaries.append("t")
    if r1 != img.shape[1]:
        boundaries.append("b")
    
    return(boundaries)

def tiled_segmentation_overlap(img, start_row, start_col, stop_row, stop_col, step_size_row, step_size_col, dummy_var, overlap = 0, cutoff=2, background_threshold = 0.1, compartment='whole-cell', app=None, postprocess_kwargs_whole_cell={}, postprocess_kwargs_nuclear={}):
    if compartment in ["whole-cell", "nuclear"]:
        mask_array = np.expand_dims(np.full_like(img, -99, dtype=int)[:,:,:,0], 3)
    elif compartment == "both":
        mask_array = np.full_like(img, -99, dtype=int)
    
    if app == None:
        app = Mesmer()

    max_current_cell_id = np.zeros(mask_array.shape[3]) 
    
    for row in range(start_row, stop_row, step_size_row):
        for col in range(start_col, stop_col, step_size_col):
            r0, r1 = np.maximum(row - overlap, 0), np.minimum(np.maximum(row - overlap, 0) + step_size_row, img.shape[1])
            c0, c1 = np.maximum(col - overlap, 0), np.minimum(np.maximum(col - overlap, 0) + step_size_col, img.shape[2])
                        
            boundaries = determine_boundaries(img, r0,r1,c0,c1)
            
            if np.max(img[:,:,:,:]) < background_threshold:
                tmp_segmentation = np.zeros_like(mask_array, dtype=int)[:, r0:r1, c0:c1,:]
            else:
                tmp_segmentation = app.predict(img[:, r0:r1, c0:c1,:], compartment=compartment, postprocess_kwargs_whole_cell=postprocess_kwargs_whole_cell, postprocess_kwargs_nuclear=postprocess_kwargs_whole_cell)

                for j in range(tmp_segmentation.shape[3]):
                    tmp_segmentation[0,:,:,j] = remove_boundary_mask(tmp_segmentation[0,:,:,j], cutoff, boundaries, dummy_var)

                    tmp_segmentation[0,:,:,j] = make_cell_mask_unique(tmp_segmentation[0,:,:,j], dummy_var, max_current_cell_id[j])
                    max_current_cell_id[j] = np.maximum(0,np.max(tmp_segmentation[0,:,:,j]))
            for j in range(tmp_segmentation.shape[3]):        
                ### remove overlapping ids
                insert_mask = np.isin(mask_array[0, r0:r1, c0:c1, j], dummy_var)
                mask_array[0, r0:r1, c0:c1, j][insert_mask] = tmp_segmentation[0,:,:,j][insert_mask]

    gc.collect()
    return(mask_array)

def getval_array(d):
    # based on https://stackoverflow.com/a/46870227
    v = np.array(list(d.values()))
    k = np.array(list(d.keys()))
    maxv = k.max()
    minv = k.min()
    n = maxv - minv + 1
    val = np.empty(n,dtype=v.dtype)
    val[k] = v
    return val


def make_cell_mask_unique(input_array, dummy_var, offset):
    cell_ids = np.unique(input_array)
    cell_ids = cell_ids[~np.isin(cell_ids, [dummy_var, 0])]
    
    transdict = {cell_ids[n] : n + offset + 1 for n in range(0,cell_ids.shape[0])}
    transdict.update({0 : 0})
    transdict.update({dummy_var : dummy_var})
    
    val_arr = getval_array(transdict)
    out = val_arr[input_array]
    
    return(out)


def _combine_overlapping_masks(mask_x, mask_y, dummy_var):
    max_cell_id_x = np.max(mask_x)

    mask_out_x = make_cell_mask_unique(mask_x, dummy_var, 0)
    mask_out_y = make_cell_mask_unique(mask_y, dummy_var, max_cell_id_x)

    # mask_xy = np.copy(mask_x)
    mask_x[np.isin(mask_out_x, dummy_var)] = mask_out_y[np.isin(mask_out_x, dummy_var)]
    gc.collect()
    return(mask_x)

def predict_tiled(img, tile_size_row=None, tile_size_col=None, dummy_var=-99, overlap=0, cutoff=2, background_threshold= 0.1, infer_gaps = False, compartment='whole-cell', app=None, postprocess_kwargs_whole_cell={}, postprocess_kwargs_nuclear={}):
    #   ensure the image has 4 dimensions to start with and that the last one is 2 dims
    if len(img.shape) != 4:
        raise ValueError(f"Image data must be 4D, got image of shape {img.shape}")
    if img.shape[3] != 2:
        raise ValueError(f"Each FOV/slide must have 2 channels, the image has {img.shape[3]} channels")
    
    
    #   iterate over the first dimension
    for fov_idx in range(img.shape[0]):
        fov = img[[fov_idx], ...]
        overlap = overlap if infer_gaps == True else 0
        tile = tile_sizer(fov.shape[2], fov.shape[1], overlap)
        
        step_size_row = tile["row_tile_size"] if tile_size_row == None else tile_size_row
        step_size_col = tile["col_tile_size"] if tile_size_col == None else tile_size_col
        overlap_tiles = tile["overlap"]
        
        print("The tile size chosen is: " + str(step_size_row) +"px X " + str(step_size_col) + "px\nThe overlap is: " + str(overlap_tiles) +"px")

        start_row, start_col, stop_row, stop_col = 0, 0, fov.shape[1], fov.shape[2]
        
        _mask = tiled_segmentation_overlap(fov, start_row, start_col, stop_row, stop_col, step_size_row, step_size_col, dummy_var,overlap = overlap_tiles, cutoff = cutoff, background_threshold = background_threshold, compartment = compartment, app=app, postprocess_kwargs_whole_cell=postprocess_kwargs_whole_cell, postprocess_kwargs_nuclear=postprocess_kwargs_nuclear)
        _mask[np.isin(_mask, [-99])] = 0
        
        for j in range(_mask.shape[3]):
            _mask[:,:,:,j] = make_cell_mask_unique(_mask[:,:,:,j], -99, 0)
        
        if fov_idx == 0:
            if img.shape[0] == 1:
                return(_mask)
            else:
                mask = np.copy(_mask)
        else:
            mask = np.concatenate([mask, _mask], axis=0)
        
        gc.collect()
        
    return(mask)
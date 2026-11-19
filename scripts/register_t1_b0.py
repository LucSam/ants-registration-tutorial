#!/usr/bin/env python3
"""Extract a mean b0 and align a brain-extracted T1, preserving T1 voxel spacing.

Inputs must already have appropriate motion, eddy-current and susceptibility
correction. This script does not perform diffusion preprocessing.
"""
from pathlib import Path
import argparse
import json
import os
os.environ.setdefault('ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS', '4')
import ants
import numpy as np
import nibabel as nib


def register(t1_path, dwi_path, bvals_path, b0_mask_path, output, threshold=50):
    t1_path, dwi_path, bvals_path, b0_mask_path = map(Path, (t1_path, dwi_path, bvals_path, b0_mask_path))
    output = Path(output)
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError('The b0 threshold must be finite and nonnegative.')
    dwi = nib.load(dwi_path)
    bvals = np.loadtxt(bvals_path).reshape(-1)
    if len(dwi.shape) != 4 or bvals.size != dwi.shape[3]:
        raise ValueError('Supply a 4D diffusion image with one b-value per volume.')
    if not np.isfinite(bvals).all() or (bvals < 0).any():
        raise ValueError('B-values must be finite and nonnegative.')
    selected = np.flatnonzero(bvals <= threshold)
    if selected.size == 0:
        raise ValueError('No b0 volumes match the threshold.')
    mask_nii = nib.load(b0_mask_path)
    if mask_nii.shape != dwi.shape[:3] or not np.allclose(mask_nii.affine, dwi.affine):
        raise ValueError('The b0 brain mask must share the diffusion spatial grid.')
    if not np.isfinite(mask_nii.get_fdata()).all() or not np.any(mask_nii.get_fdata() > 0):
        raise ValueError('The b0 brain mask is empty or non-finite.')
    # Read only selected volumes; do not load the whole diffusion series into RAM.
    mean = np.zeros(dwi.shape[:3], dtype=np.float32)
    for index in selected:
        volume = np.asarray(dwi.dataobj[..., int(index)], dtype=np.float32)
        if not np.isfinite(volume).all():
            raise ValueError('Non-finite intensities in a selected b0 volume.')
        mean += volume / selected.size
    output.mkdir(parents=True, exist_ok=True)
    b0_path = output / 'mean_b0.nii.gz'
    nib.save(nib.Nifti1Image(mean, dwi.affine), b0_path)
    b0 = ants.image_read(str(b0_path))
    mask = ants.image_read(str(b0_mask_path)) > 0
    fixed = b0 * mask
    moving = ants.image_read(str(t1_path))
    if moving.dimension != 3:
        raise ValueError('T1 must be a 3D brain-extracted image.')
    result = ants.registration(fixed=fixed, moving=moving, type_of_transform='Rigid',
                               aff_metric='mattes', mask=mask, moving_mask=moving > 0,
                               mask_all_stages=True, outprefix=str(output / 'T1toB0_'))
    fine_reference = ants.resample_image(b0, moving.spacing, use_voxels=False, interp_type=0)
    coarse = ants.apply_transforms(fixed=b0, moving=moving,
                                   transformlist=result['fwdtransforms'], interpolator='linear')
    fine = ants.apply_transforms(fixed=fine_reference, moving=moving,
                                 transformlist=result['fwdtransforms'], interpolator='linear')
    assert np.allclose(fine.spacing, moving.spacing)
    ants.image_write(coarse, str(output / 'T1_on_b0_grid.nii.gz'))
    ants.image_write(fine, str(output / 'T1_in_b0_space_T1_spacing.nii.gz'))
    record = {'b0_indices': selected.tolist(), 'b0_threshold_s_per_mm2': threshold,
              'transform': 'Rigid', 'b0_spacing_mm': list(b0.spacing),
              'input_T1_spacing_mm': list(moving.spacing), 'output_T1_spacing_mm': list(fine.spacing),
              'fine_output_origin': list(fine.origin), 'fine_output_direction': fine.direction.tolist()}
    (output / 'geometry.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--t1', required=True, help='Bias-corrected, brain-extracted 3D T1')
    p.add_argument('--dwi', required=True, help='Preprocessed 4D diffusion image')
    p.add_argument('--bvals', required=True, help='Matching b-values')
    p.add_argument('--b0-mask', required=True, help='Brain mask on the diffusion spatial grid')
    p.add_argument('--output', required=True)
    p.add_argument('--b0-threshold', type=float, default=50, help='Maximum b-value treated as b0, s/mm² (default 50)')
    args = p.parse_args()
    result = register(args.t1, args.dwi, args.bvals, args.b0_mask, args.output, args.b0_threshold)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

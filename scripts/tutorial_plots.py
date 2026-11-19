"""Plotting helpers. Registration and resampling are shown in the notebook."""
import numpy as np
import nibabel as nib
from nibabel.processing import resample_from_to
from scipy.ndimage import binary_fill_holes
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, TwoSlopeNorm
from matplotlib.patches import Patch, Rectangle

VIEW_WIDTH_MM = 220.0
FIGURE_WIDTH_IN = 12.0
PANEL_WIDTH_IN = 3.4
PANEL_LEFTS_IN = (.75, 4.4, 8.05)


def _panel_figure(rows=1):
    """Use fixed panel positions so colorbars and labels cannot resize images."""
    height = 4.8 if rows == 1 else 9.6
    fig = plt.figure(figsize=(FIGURE_WIDTH_IN, height))
    axes = np.empty((rows, 3), dtype=object)
    for row in range(rows):
        bottom = .8 + (rows - row - 1) * 4.1
        for column in range(3):
            left = PANEL_LEFTS_IN[column]
            axes[row, column] = fig.add_axes(
                [left / FIGURE_WIDTH_IN, bottom / height,
                 PANEL_WIDTH_IN / FIGURE_WIDTH_IN, PANEL_WIDTH_IN / height])
    return fig, axes


def _show_figure(fig, destination):
    """Preserve the canvas dimensions in saved files and notebook outputs."""
    if destination is not None:
        fig.savefig(destination, dpi=160, bbox_inches=None)
        try:
            from IPython import get_ipython
            from IPython.display import Image, display
        except ImportError:
            pass
        else:
            if get_ipython() is not None:
                display(Image(filename=str(destination)))
                plt.close(fig)
                return
    plt.show()


def ras(path):
    return nib.as_closest_canonical(nib.load(path))


def values(path):
    return ras(path).get_fdata(dtype=np.float32)


def normalized(array):
    low, high = np.percentile(array[array > 0], [2, 98])
    return np.clip((array - low) / max(high - low, 1e-6), 0, 1)


def _extent(image, axis):
    """Slice bounds in millimetres along the two displayed voxel axes."""
    dimensions = [dimension for dimension in range(3) if dimension != axis]
    return tuple(bound for dimension in dimensions
                 for bound in (-image.header.get_zooms()[dimension] / 2,
                               (image.shape[dimension] - .5) * image.header.get_zooms()[dimension]))


def _square_panel(ax, extent, axis=2, title=None, coordinates=False, side=VIEW_WIDTH_MM):
    """Pad the view to a square and label radiological orientation."""
    xmin, xmax, ymin, ymax = extent
    xcenter, ycenter = (xmin + xmax) / 2, (ymin + ymax) / 2
    xlimits = (xcenter - side / 2, xcenter + side / 2)
    ax.set_xlim(xlimits if axis == 0 else xlimits[::-1])
    ax.set_ylim(ycenter - side / 2, ycenter + side / 2)
    ax.set_box_aspect(1)
    ax.set_aspect('equal', adjustable='box')
    ax.set_facecolor('black')
    for spine in ax.spines.values():
        spine.set_visible(False)
    if not coordinates:
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        ax.tick_params(labelsize=9)
    left, right, top, bottom = ('P', 'A', 'S', 'I') if axis == 0 else (
        ('R', 'L', 'S', 'I') if axis == 1 else ('R', 'L', 'A', 'P'))
    for x, y, label, ha, va in ((.025, .5, left, 'left', 'center'),
                               (.975, .5, right, 'right', 'center'),
                               (.5, .975, top, 'center', 'top'),
                               (.5, .025, bottom, 'center', 'bottom')):
        ax.text(x, y, label, transform=ax.transAxes, color='white', fontsize=10,
                ha=ha, va=va, bbox={'facecolor': 'black', 'edgecolor': 'none', 'alpha': .65, 'pad': 1})
    if title:
        ax.set_title(title, fontsize=12)


def show_n4(raw_path, corrected_path, field_path, label_path, destination, contrast='T1c',
            axial_slice=None):
    raw_image = ras(raw_path)
    raw, corrected, field = [values(p) for p in (raw_path, corrected_path, field_path)]
    labels = values(label_path)
    z = int(np.argmax((labels > 0).sum(axis=(0, 1)))) if axial_slice is None else int(axial_slice)
    if not 0 <= z < raw.shape[2]:
        raise ValueError('axial_slice must be within the native T1 volume.')
    low, high = np.percentile(raw[raw > 0], [2, 98])
    delta = max(float(np.percentile(np.abs(field[raw > 0] - 1), 99)), 0.01)
    fig, panel_axes = _panel_figure()
    axes = panel_axes[0]
    colorbar_axis = fig.add_axes([PANEL_LEFTS_IN[1] / FIGURE_WIDTH_IN, .38 / 4.8,
                                 PANEL_WIDTH_IN / FIGURE_WIDTH_IN, .10 / 4.8])
    extent = _extent(raw_image, 2)
    for ax, pixels, title in zip(axes, [raw, field, corrected],
                                  [f'Input {contrast}', 'Estimated N4 bias field', f'N4-corrected {contrast}']):
        if ax is axes[1]:
            display = np.ma.masked_where(raw[:, :, z].T <= 0, pixels[:, :, z].T)
            plot = ax.imshow(display, origin='lower', cmap='jet', extent=extent,
                             interpolation='nearest',
                             norm=TwoSlopeNorm(vmin=1-delta, vcenter=1, vmax=1+delta))
            colorbar = fig.colorbar(plot, cax=colorbar_axis, orientation='horizontal',
                                   ticks=np.linspace(1-delta, 1+delta, 5),
                                   format='%.2f', label='Multiplicative gain B')
            colorbar.ax.axvline(1, color='black', linewidth=0.8)
        else:
            ax.imshow(pixels[:, :, z].T, origin='lower', cmap='gray', extent=extent,
                      vmin=low, vmax=high, interpolation='nearest')
        _square_panel(ax, extent, title=title)
    _show_figure(fig, destination)


def show_cars(images, destination):
    titles = ['Fixed car (a)', 'Moving car (b)',
              'Forward: b → a', 'Inverse: a → b']
    fig, axes = plt.subplots(2, 2, figsize=(12, 6.5), layout='constrained')
    for ax, image, title in zip(axes.flat, images, titles):
        ax.imshow(image.numpy().T, cmap='gray', vmin=0, vmax=255, origin='upper')
        ax.set_title(title, fontsize=12)
        ax.axis('off')
    fig.savefig(destination, dpi=150, bbox_inches='tight')
    plt.show()


def show_sampling(target_path, coarse_path, fine_path, destination, *, reference_brain_path):
    """Compare physical alignment and voxel sampling at the same MNI locations."""
    fine = ras(fine_path)
    target, coarse = [ras(p) for p in (target_path, coarse_path)]
    target_view = resample_from_to(target, fine, order=0).get_fdata(dtype=np.float32)
    coarse_view = resample_from_to(coarse, fine, order=0).get_fdata(dtype=np.float32)
    fine_view = fine.get_fdata(dtype=np.float32)
    # Derive the anatomical outline before smoothing creates nonzero values outside the brain.
    reference = ras(reference_brain_path)
    reference_mask = nib.Nifti1Image(
        (reference.get_fdata(dtype=np.float32) > 0).astype(np.uint8), reference.affine,
    )
    reference_mask_view = resample_from_to(reference_mask, fine, order=0).get_fdata() > 0
    z = int(np.argmin(np.abs(fine.affine[2, 3] + np.arange(fine.shape[2]) * fine.affine[2, 2] - 18)))
    outer_mask = binary_fill_holes(reference_mask_view[:, :, z])
    spacing = np.diag(fine.affine)[:3]
    origin = fine.affine[:3, 3]
    extent = [origin[0]-spacing[0]/2, origin[0]+spacing[0]*(fine.shape[0]-.5),
              origin[1]-spacing[1]/2, origin[1]+spacing[1]*(fine.shape[1]-.5)]
    xs = origin[0] + np.arange(fine.shape[0]) * spacing[0]
    ys = origin[1] + np.arange(fine.shape[1]) * spacing[1]
    low, high = np.percentile(fine_view[fine_view > 0], [2, 98])
    target_low, target_high = np.percentile(target_view[target_view > 0], [2, 98])
    roi = (32, 68, -42, -6)  # Identical 36 × 36 mm region in all three panels.
    selected_x = np.flatnonzero((xs >= roi[0]) & (xs <= roi[1]))
    selected_y = np.flatnonzero((ys >= roi[2]) & (ys <= roi[3]))
    fine_zoom = fine_view[:, :, z][np.ix_(selected_x, selected_y)]
    target_zoom = target_view[:, :, z][np.ix_(selected_x, selected_y)]
    zoom_low, zoom_high = np.percentile(fine_zoom[fine_zoom > 0], [2, 98])
    target_zoom_low, target_zoom_high = np.percentile(target_zoom[target_zoom > 0], [2, 98])
    fig, axes = _panel_figure(rows=2)
    titles = ['Registration target\nMNI at 3 mm',
              'After registration\nT1 sampled at 3 mm', 'Same transform\nT1 sampled at 1 mm']
    arrays = [target_view, coarse_view, fine_view]
    grids = [target, coarse, fine]
    for column, (array, title, grid) in enumerate(zip(arrays, titles, grids)):
        for row in range(2):
            ax = axes[row, column]
            window = ((target_low, target_high) if column == 0 else (low, high))
            if row == 1:
                window = ((target_zoom_low, target_zoom_high) if column == 0 else (zoom_low, zoom_high))
            ax.imshow(array[:, :, z].T, origin='lower', extent=extent, cmap='gray',
                      vmin=window[0], vmax=window[1], interpolation='nearest')
            ax.contour(xs, ys, outer_mask.T, levels=[.5],
                       colors=['#26bfd1'], linewidths=.65)
            if row == 0:
                ax.add_patch(Rectangle((roi[0], roi[2]), roi[1]-roi[0], roi[3]-roi[2],
                                       fill=False, edgecolor='#e2ae46', linewidth=1.2))
                _square_panel(ax, extent, title=title)
            else:
                _square_panel(ax, roi, coordinates=True, side=roi[1] - roi[0])
                ax.set_xlabel('MNI x (mm)', fontsize=10)
                if column == 0:
                    ax.set_ylabel('MNI y (mm)', fontsize=10)
                if grid is not None:
                    for dimension in (0, 1):
                        step = grid.affine[dimension, dimension]
                        first = grid.affine[dimension, 3] - step/2
                        lines = first + np.arange(grid.shape[dimension] + 1) * step
                        for value in lines:
                            if dimension == 0 and roi[0] <= value <= roi[1]:
                                ax.axvline(value, color='white', alpha=.25, linewidth=.45)
                            elif dimension == 1 and roi[2] <= value <= roi[3]:
                                ax.axhline(value, color='white', alpha=.25, linewidth=.45)
                ax.tick_params(labelsize=9)
    fig.suptitle('One estimated transform, two output grids\nCyan: original MNI brain mask. Gold: the region enlarged below.', fontsize=13, y=.975)
    _show_figure(fig, destination)


def _orthogonal_view(fixed_image, fixed, moving, title, mode='Overlay', position=50,
                     alpha=.45, destination=None, labels=False):
    fig, panel_axes = _panel_figure()
    axes = panel_axes[0]
    if labels:
        label_ids = np.unique(moving[moving > 0])
        colors = plt.get_cmap('tab10').colors[:len(label_ids)]
        label_cmap = ListedColormap(colors) if len(label_ids) else None
    for axis, (ax, plane) in enumerate(zip(axes, ['Sagittal', 'Coronal', 'Axial'])):
        index = int(round(position / 100 * (fixed.shape[axis] - 1)))
        fs = np.take(fixed, index, axis=axis).T
        ms = np.take(moving, index, axis=axis).T
        extent = _extent(fixed_image, axis)
        if mode == 'Checkerboard':
            yy, xx = np.indices(fs.shape)
            tiles = (xx // 12 + yy // 12) % 2 == 0
            ax.imshow(np.where(tiles, fs, ms), origin='lower', extent=extent,
                      cmap='gray', vmin=0, vmax=1, interpolation='nearest')
        else:
            ax.imshow(fs, origin='lower', extent=extent, cmap='gray', vmin=0, vmax=1,
                      interpolation='nearest')
            if labels:
                if len(label_ids):
                    mapped = np.ma.masked_where(ms <= 0, np.searchsorted(label_ids, ms))
                    ax.imshow(mapped, origin='lower', extent=extent, cmap=label_cmap,
                              vmin=-.5, vmax=len(label_ids)-.5, alpha=alpha,
                              interpolation='nearest')
            else:
                ax.imshow(np.ma.masked_where(ms <= 0, ms), origin='lower', extent=extent,
                          cmap='jet', vmin=0, vmax=1, alpha=alpha, interpolation='nearest')
        _square_panel(ax, extent, axis=axis, title=f'{plane}: slice {index}')
    fig.suptitle(title, fontsize=13, y=.975)
    if labels and len(label_ids):
        handles = [Patch(facecolor=color, label=f'Label {value:g}')
                   for color, value in zip(colors, label_ids)]
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .035),
                   ncol=len(handles), frameon=False)
    _show_figure(fig, destination)


def show_registration(fixed_path, moving_path, destination, title, labels=False):
    """Show three square views of a saved registration or transformed labels."""
    fixed_image, moving_image = ras(fixed_path), ras(moving_path)
    if moving_image.shape != fixed_image.shape or not np.allclose(moving_image.affine, fixed_image.affine):
        raise ValueError('The overlay and reference must occupy the same physical grid.')
    fixed = normalized(fixed_image.get_fdata(dtype=np.float32))
    moving = moving_image.get_fdata(dtype=np.float32)
    if not labels:
        moving = normalized(moving)
    _orthogonal_view(fixed_image, fixed, moving, title, destination=destination, labels=labels)


def make_qc(fixed_path, image_paths, destination=None):
    fixed_image = ras(fixed_path)
    fixed = normalized(fixed_image.get_fdata(dtype=np.float32))
    images = {}
    for method, path in image_paths.items():
        image = ras(path)
        if image.shape != fixed_image.shape or not np.allclose(image.affine, fixed_image.affine):
            raise ValueError(f'{method}: QC inputs must occupy the same physical grid.')
        images[method] = normalized(image.get_fdata(dtype=np.float32))

    def registration_qc(method='SyN', mode='Checkerboard', position=50, alpha=.5):
        _orthogonal_view(fixed_image, fixed, images[method],
                         f'{method}, {mode}: MNI and registered T1', mode=mode,
                         position=position, alpha=alpha, destination=destination)

    return registration_qc

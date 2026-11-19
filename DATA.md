<a id="data-and-attribution"></a>
# 6. Data and attribution

The project includes approximately 10 MB of example images. Sources, citations and reuse terms are listed below for each input.

<a id="ucsf-data"></a>
## 6.1 UCSF-PDGM-0033: T1, T1c and tumor labels

Source: [UCSF-PDGM at The Cancer Imaging Archive](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/), Version 5, downloaded directly from TCIA. License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). Redistribution is permitted with attribution and a license link; indicate changes. The supplied NIfTI inputs are unmodified. N4 and resampled images are generated separately under `outputs/`.

| Input | Use |
|---|---|
| `UCSF-PDGM-0033_T1c.nii.gz` | Postcontrast T1; the default input |
| `UCSF-PDGM-0033_T1.nii.gz` | Precontrast alternative |
| `UCSF-PDGM-0033_tumor_segmentation.nii.gz` | Lesion exclusion and label propagation |

All three have a 240 × 240 × 155 matrix and 1 × 1 × 1 mm spacing. The dataset authors co-registered and resampled the structural contrasts to the subject's FLAIR grid, then skull stripped them. Stored spacing is not a claim about native acquisition resolution. Official paths, sizes and SHA-256 hashes are in `data/UCSF-PDGM-0033/provenance.json`.

Dataset citation: Calabrese E, Villanueva-Meyer J, Rudie J, Rauschecker A, Baid U, Bakas S, Cha S, Mongan J, Hess C. (2022). *The University of California San Francisco Preoperative Diffuse Glioma MRI (UCSF-PDGM)* (Version 5) [dataset]. The Cancer Imaging Archive. [doi:10.7937/tcia.bdgf-8v37](https://doi.org/10.7937/tcia.bdgf-8v37).

Paper: Calabrese et al. (2022). *The University of California San Francisco Preoperative Diffuse Glioma MRI Dataset*. Radiology: Artificial Intelligence. [doi:10.1148/ryai.220058](https://doi.org/10.1148/ryai.220058). Follow the [TCIA data usage policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/).

### Optional re-download from TCIA

Install [IBM Aspera Connect](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/) and the Python dependencies, then run from the project folder:

```bash
.venv/bin/python download_ucsf_example.py
```

The script requests only T1, T1c and labels (approximately 6.7 MB). It verifies and reuses matching files, checks geometry and stages new downloads before installing them. `--ascp /path/to/ascp` specifies a nonstandard Aspera installation. No personal password is required. It uses the official TCIA service and keeps HTTPS certificate verification enabled.

<a id="mni-reference"></a>
## 6.2 MNI152 reference

`assets/MNI152_T1_1mm_brain.nii.gz` is the unmodified FSL-distributed MNI152 T1 brain template, from `fsl-data_standard` version 2208.0. Its checksum and source package are in `assets/mni_provenance.json`.

[FSL's template documentation](https://fsl.fmrib.ox.ac.uk/fsl/docs/other/datasets.html) credits Andrew Janke and identifies this image as the asymmetric counterpart of the MNI ICBM152 nonlinear sixth-generation symmetric average. The [MNI atlas page](https://www.bic.mni.mcgill.ca/ServicesAtlases/ICBM152NLin6) gives background and the associated publication: Grabner et al. (2006), [doi:10.1007/11866763_8](https://doi.org/10.1007/11866763_8).

The FSL distribution's [license notice](licenses/FSL.txt) accompanies this reference. Its non-commercial redistribution conditions must be retained; this image is not relicensed under the UCSF CC BY terms. The source and current conditions are on [FSL's license page](https://fsl.fmrib.ox.ac.uk/fsl/docs/license.html).

<a id="car-data"></a>
## 6.3 Car demonstration

The demonstration is adapted from Figure 9 on page 16 of the [ANTs manual](https://gaetanbelhomme.wordpress.com/wp-content/uploads/2016/08/ants2.pdf#page=16) and its [companion car example](https://stnava.github.io/cars/). The photographs in `assets/a.png` and `assets/b.png` are a different pair from the Ford/Beetle pair in that figure. This reference establishes the origin of the registration demonstration, not the authorship of these photographs.

<a id="derived-outputs"></a>
## 6.4 Derived outputs

N4 correction, registration, mean-b0 extraction and resampling write derived files to `outputs/`. Supplied inputs remain unchanged. The MNI resolution exercise creates its 3 mm target locally. The optional T1-to-b0 script requires the reader's own preprocessed diffusion series, b-values and brain mask; it does not download diffusion data.

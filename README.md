# ANTs registration tutorial

A Jupyter tutorial on rigid, affine and SyN registration with ANTs. It starts with car photographs, then registers UCSF-PDGM-0033 brain MRI to MNI. The examples cover N4 bias correction, lesion masking, output voxel spacing, label propagation and visual inspection.

## Reading and running

| Format | Use |
|---|---|
| [HTML reading copy](docs/index.html) | Download the repository and open this file in a browser to read the explanations, code and saved figures |
| [Jupyter notebook](ants_registration_tutorial.ipynb) | Run the code, change parameters and use the slice, overlay and transform controls |

Use JupyterLab for the interactive lesson. For offline reading, download the repository and open [docs/index.html](docs/index.html) in a browser.

<a id="installation"></a>
## Install the environment

Download the repository using Code → Download ZIP and extract it, or clone it:

```bash
git clone https://github.com/LucSam/ants-registration-tutorial.git
cd ants-registration-tutorial
```

Open a terminal in the project directory containing `setup_tutorial.py`. Use Python 3.10–3.12. The examples were run with Python 3.12 and ANTsPy 0.5.4 on macOS.

```bash
python3 setup_tutorial.py
python3 setup_tutorial.py --install
```

The first command reports installed dependencies and missing inputs. `--install` creates a virtual environment in `.venv`, installs the Python packages there and registers its Jupyter kernel. Package constraints are in [requirements.txt](requirements.txt).

The approximately 10 MB input set is included: UCSF-PDGM-0033 T1, T1c and tumor labels, the 1 mm MNI image and the car photographs.

<a id="run-notebook"></a>
## Run the notebook

From the project directory, start JupyterLab:

```bash
.venv/bin/python -m jupyterlab ants_registration_tutorial.ipynb
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.
Select the ANTs registration tutorial kernel. Run the cells from the start, or choose Run → Run All Cells. The tutorial has six numbered chapters:

1. Introduction: the car example.
2. Prepare the MRI: images, N4 correction and masks.
3. Register the MRI: model choice, rigid/affine/SyN examples and terminal commands.
4. Output and quality checks: voxel spacing, T1-to-b0 adaptation, labels and registration assessment.
5. References.
6. Data and attribution.

The controls in section 4.4 become available after the preceding cells have run. Generated images, transforms and logs are written to `outputs/`.

<a id="optional-components"></a>
## Optional components

- ANTs command-line tools: section 3.5 uses `antsRegistration`, `antsApplyTransforms`, `antsRegistrationSyNQuick.sh` and Bash. Follow the [official ANTs installation instructions](https://github.com/ANTsX/ANTs/wiki/Installing-ANTs-release-binaries), add the executables to `PATH`, then run `python3 setup_tutorial.py --require-cli`.
- ANTsPyNet: section 2.3 includes a brain-extraction branch for your own unstripped images. Install it with `python3 setup_tutorial.py --install --with-brain-extraction`. This includes TensorFlow; the first brain-extraction call downloads pretrained weights.

## Create the reading copy

After running and saving the notebook, export it:

```bash
.venv/bin/python scripts/build_book.py
```

The exporter creates [docs/index.html](docs/index.html) with all six chapters and the saved figures. A second copy is written under `outputs/UCSF-PDGM-0033/`.

Edit the data and attribution text in [DATA.md](DATA.md). The exporter synchronizes this text with chapter 6 in the notebook before creating the HTML page.

## Project files

| File or directory | Purpose |
|---|---|
| [ants_registration_tutorial.ipynb](ants_registration_tutorial.ipynb) | Source notebook for JupyterLab |
| [DATA.md](DATA.md) | Source text for chapter 6: data and attribution |
| `docs/` | HTML reading copy and its attribution notices |
| `assets/` | MNI reference, car images and MNI provenance |
| `data/UCSF-PDGM-0033/` | T1, T1c, tumor labels and TCIA provenance |
| `outputs/` | Generated images, transforms, QC figures, reading copies and logs |
| `scripts/register_mri.sh` | Terminal example; run after notebook chapter 2 |
| `scripts/register_t1_b0.py` | Mean b0 extraction and T1 registration using your own preprocessed diffusion data |
| `scripts/tutorial_plots.py` | Plotting helpers |
| `scripts/build_book.py` | HTML exporter |
| `licenses/` | Third-party notices for the supplied reference data |

The public MRI is from [UCSF-PDGM at TCIA](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/), distributed under CC BY 4.0. The MNI reference has separate redistribution terms. See [Data and attribution](DATA.md) for image sources, citations and reuse terms.

Lucius Fekonja · 2026

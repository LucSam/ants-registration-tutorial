#!/usr/bin/env bash
# Run after notebook chapter 2 has written the corrected brain and metric mask.
set -euo pipefail
cd "$(dirname "$0")/.."
model="${1:-syn}"
case "$model" in
  rigid) mode=r; prefix=outputs/UCSF-PDGM-0033/mri/T1toMNI_cli_Rigid_ ;;
  affine) mode=a; prefix=outputs/UCSF-PDGM-0033/mri/T1toMNI_cli_Affine_ ;;
  syn) mode=s; prefix=outputs/UCSF-PDGM-0033/mri/T1toMNI_ ;;
  *) echo 'Usage: bash scripts/register_mri.sh rigid|affine|syn' >&2; exit 2 ;;
esac
for command in antsRegistrationSyNQuick.sh antsRegistration antsApplyTransforms; do
  command -v "$command" >/dev/null || { echo "Missing $command; see README.md." >&2; exit 1; }
done
fixed=assets/MNI152_T1_1mm_brain.nii.gz
moving=outputs/UCSF-PDGM-0033/mri/t1_brain.nii.gz
mask=outputs/UCSF-PDGM-0033/mri/included_tissue.nii.gz
labels=data/UCSF-PDGM-0033/UCSF-PDGM-0033_tumor_segmentation.nii.gz
for input in "$fixed" "$moving" "$mask" "$labels"; do
  test -f "$input" || { echo "Missing $input. Run notebook chapter 2 first." >&2; exit 1; }
done
log="${prefix}run.log"
if ! antsRegistrationSyNQuick.sh -d 3 -f "$fixed" -m "$moving" \
    -x "NULL,$mask" -t "$mode" -o "$prefix" >"$log" 2>&1; then
  tail -n 30 "$log" >&2
  exit 1
fi
transforms=(-t "${prefix}0GenericAffine.mat")
if [ "$mode" = s ]; then
  transforms=(-t "${prefix}1Warp.nii.gz" "${transforms[@]}")
fi
if ! antsApplyTransforms -d 3 -i "$labels" -r "$fixed" \
    -o "${prefix}labels.nii.gz" -n NearestNeighbor "${transforms[@]}" >>"$log" 2>&1; then
  tail -n 30 "$log" >&2
  exit 1
fi
echo "Saved ${prefix}Warped.nii.gz; details: $log"

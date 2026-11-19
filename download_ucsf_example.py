#!/usr/bin/env python3
"""Download the UCSF-PDGM structural tutorial case directly from TCIA."""
import argparse
import base64
from datetime import datetime, timezone
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from pathlib import PurePosixPath
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
DEFAULT_CASE = "UCSF-PDGM-0033"
COLLECTION = "https://www.cancerimagingarchive.net/collection/ucsf-pdgm/"
FASPEX = "https://faspex.cancerimagingarchive.net/aspera/faspex"
PACKAGE_ID = "1065"  # Official TCIA Version 5 package.
# Public passphrase for Aspera's bundled token-authentication key, not a user
# account password. Documented at https://hpc.nih.gov/docs/transfer (Aspera).
TOKENAUTH_KEY_PASSPHRASE = "743128bf-3bf3-45b5-ab14-4602c67f2950"


def normalize_case(value):
    """Accept 0033 or UCSF-PDGM-0033, without accepting arbitrary paths."""
    match = re.fullmatch(r"(?:UCSF-PDGM-)?(\d{1,4})", value)
    if not match or int(match.group(1)) == 0:
        raise argparse.ArgumentTypeError("Use a case number such as 0033 or UCSF-PDGM-0033.")
    return f"UCSF-PDGM-{int(match.group(1)):04d}"


def case_files(case_id):
    return tuple(f"{case_id}_{suffix}" for suffix in (
        "T1c.nii.gz", "tumor_segmentation.nii.gz", "T1.nii.gz",
    ))


class CollectionLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


@lru_cache(maxsize=1)
def https_context():
    """Keep TLS verification enabled when Python's default CA store is empty."""
    context = ssl.create_default_context()
    # Respect explicitly configured trust stores. Python.org macOS installs can
    # otherwise have no roots until their Install Certificates command is run.
    if (context.cert_store_stats()["x509_ca"] == 0 and
            not any(os.environ.get(key) for key in ("SSL_CERT_FILE", "SSL_CERT_DIR"))):
        try:
            import certifi
        except ImportError:
            system_bundle = Path("/etc/ssl/cert.pem")
            if system_bundle.is_file():
                context.load_verify_locations(cafile=str(system_bundle))
        else:
            context.load_verify_locations(cafile=certifi.where())
    return context


def request_bytes(url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, timeout=120, context=https_context()) as response:
        return response.read()


def public_token(collection_html, client_config, opener=None):
    """Exchange TCIA's public collection link for a short-lived download token."""
    links = CollectionLinks()
    links.feed(collection_html)
    context = None
    for link in links.links:
        if not link.startswith(FASPEX):
            continue
        candidates = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("context", [])
        if not candidates:
            continue
        decoded = json.loads(base64.b64decode(candidates[0]))
        if str(decoded.get("package_id")) == PACKAGE_ID:
            context = candidates[0]
            break
    if context is None:
        raise RuntimeError("TCIA's Version 5 link changed; check DATA.md and the collection page.")
    config = {}
    for key in ("client_id", "redirect_uri"):
        match = re.search(r"\b" + key + r"\s*:\s*['\"]([^'\"]+)", client_config)
        if not match:
            raise RuntimeError("Could not read TCIA's public download client configuration.")
        config[key] = match.group(1)
    query = urllib.parse.urlencode(dict(response_type="code", state=context, **config))
    opener = opener or urllib.request.build_opener(
        NoRedirect, urllib.request.HTTPSHandler(context=https_context())
    )
    try:
        response = opener.open(FASPEX + "/auth/authorize_public_link?" + query, timeout=120)
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        response = error
    try:
        location = response.headers.get("Location", "")
    finally:
        response.close()
    code = urllib.parse.parse_qs(urllib.parse.urlparse(location).query).get("code", [])
    if not code:
        raise RuntimeError("TCIA did not authorize its public download link.")
    form = urllib.parse.urlencode(dict(grant_type="authorization_code", code=code[0], **config))
    token = json.loads(request_bytes(FASPEX + "/auth/token", data=form.encode()))
    return token["access_token"]


def find_ascp(explicit=None):
    candidates = [Path(explicit)] if explicit else []
    if shutil.which("ascp"):
        candidates.append(Path(shutil.which("ascp")))
    candidates.extend([
        Path.home() / "Applications/Aspera Connect.app/Contents/Resources/ascp",
        Path("/Applications/Aspera Connect.app/Contents/Resources/ascp"),
        Path.home() / ".aspera/connect/bin/ascp",
    ])
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("Aspera's ascp was not found. Supply --ascp /path/to/ascp.")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_existing(directory, case_id=DEFAULT_CASE):
    """Verify official provenance and hashes before reusing existing inputs."""
    record_path = directory / "provenance.json"
    if not record_path.exists():
        return False
    record = json.loads(record_path.read_text())
    if (record.get("case_id") != case_id or record.get("collection_url") != COLLECTION or
            record.get("package_id") != PACKAGE_ID or record.get("source") != "TCIA"):
        raise RuntimeError("The existing provenance is not for this TCIA case; it was not overwritten.")
    entries = {item["filename"]: item for item in record.get("files", [])}
    required = set(case_files(case_id))
    if not set(entries).issubset(required):
        raise RuntimeError("Unexpected files in this case's provenance; it was not overwritten.")
    complete = required.issubset(entries)
    for name, entry in entries.items():
        if entry.get("source") != f"/UCSF-PDGM-v5/{case_id}_nifti/{name}":
            raise RuntimeError(f"Unexpected provenance source for {name}.")
        target = directory / name
        if not target.is_file():
            complete = False
            continue
        if target.stat().st_size != entry["bytes"] or sha256(target) != entry["sha256"]:
            raise RuntimeError(f"Local file differs from its download record; it was not overwritten: {target}")
    return complete


def validate_case(directory, case_id=DEFAULT_CASE):
    """Check that T1, T1c and labels share a valid 3D physical grid."""
    import nibabel as nib
    import numpy as np

    images = [nib.load(directory / name) for name in case_files(case_id)]
    t1c = images[0]
    for image in images:
        if (len(image.shape) != 3 or image.shape != t1c.shape or
                not np.allclose(image.affine, t1c.affine)):
            raise RuntimeError("T1, T1c and tumor labels must share a 3D physical grid.")
        if (not np.isfinite(image.affine).all() or
                abs(np.linalg.det(image.affine[:3, :3])) < 1e-8 or
                any(spacing <= 0 for spacing in image.header.get_zooms())):
            raise RuntimeError("Invalid NIfTI physical geometry.")
    return {"structural_contrast": "T1c", "t1_shape": list(t1c.shape),
            "t1_spacing_mm": [float(v) for v in t1c.header.get_zooms()]}


def download_case(directory, ascp_path=None, case_id=DEFAULT_CASE):
    names = case_files(case_id)
    case_folder = f"/UCSF-PDGM-v5/{case_id}_nifti"
    if verify_existing(directory, case_id):
        validate_case(directory, case_id)
        print("Verified TCIA structural case:", case_id)
        return
    # Check dependencies before starting a transfer.
    try:
        import nibabel
        import numpy
    except ImportError as error:
        raise RuntimeError("Install the notebook dependencies first: python3 -m pip install nibabel numpy") from error
    ascp = find_ascp(ascp_path)
    key_candidates = [ascp.parent / "aspera_tokenauth_id_rsa",
                      ascp.parent.parent / "etc/aspera_tokenauth_id_rsa"]
    key = next((p for p in key_candidates if p.is_file()), None)
    if key is None:
        raise RuntimeError("The Aspera installation's token authentication key was not found.")
    token = public_token(request_bytes(COLLECTION).decode(),
                         request_bytes(FASPEX + "/config.js").decode())
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    api = FASPEX + "/api/v5/packages/" + PACKAGE_ID
    listing = json.loads(request_bytes(
        api + "/files/received/page?recipient_user_id=12",
        data=json.dumps({"path": case_folder, "filters": {}}).encode(), headers=headers,
    ))
    selected = {item["basename"]: item for item in listing["items"] if item["basename"] in names}
    if set(selected) != set(names):
        raise RuntimeError(f"Requested structural files are missing from TCIA's listing for {case_id}.")
    if any(selected[name]["path"] != f"{case_folder}/{name}" for name in names):
        raise RuntimeError("Unexpected case paths in TCIA's listing.")
    record_path = directory / "provenance.json"
    existing_record = json.loads(record_path.read_text()) if record_path.exists() else {}
    recorded = {entry["filename"]: entry for entry in existing_record.get("files", [])}
    reused = [name for name in names if name in recorded and (directory / name).is_file()]
    pending = [name for name in names if name not in reused]
    spec = json.loads(request_bytes(
        api + "/transfer_spec/download?transfer_type=connect&type=received&recipient_user_id=12",
        data=json.dumps({"paths": [{"path": selected[name]["path"]} for name in pending]}).encode(),
        headers=headers,
    ))
    received_names = [PurePosixPath(item["source"]).name for item in spec.get("paths", [])]
    if (spec.get("direction") != "receive" or len(received_names) != len(pending) or
            set(received_names) != set(pending)):
        raise RuntimeError("Unexpected download specification from TCIA.")
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ucsf-case-", dir=runtime) as temporary:
        stage = Path(temporary)
        for name in reused:
            shutil.copy2(directory / name, stage / name)
        total_mb = sum(selected[name]["size"] for name in pending) / 1e6
        print(f"Downloading {case_id} directly from TCIA ({total_mb:.1f} MB):", flush=True)
        print("Precontrast T1, postcontrast T1c and tumor labels.", flush=True)
        if reused:
            print(f"Reusing {len(reused)} verified structural files.", flush=True)
        run_aspera(ascp, key, spec, stage)
        for name in names:
            received = stage / name
            if not received.is_file() or received.stat().st_size != selected[name]["size"]:
                raise RuntimeError(f"Downloaded file does not match TCIA's listed byte count: {name}")
        geometry = validate_case(stage, case_id)
        record = {"source": "TCIA", "case_id": case_id, "collection_url": COLLECTION,
                  "dataset_doi": "10.7937/tcia.bdgf-8v37", "package_id": PACKAGE_ID,
                  "license": "CC BY 4.0", "downloaded_utc": datetime.now(timezone.utc).isoformat(),
                  "geometry": geometry, "files": []}
        for name in names:
            received = stage / name
            digest = sha256(received)
            target = directory / name
            if target.exists() and sha256(target) != digest:
                raise RuntimeError(f"Existing file differs from the official download; it was not overwritten: {target}")
            entry = {"filename": name, "bytes": received.stat().st_size,
                     "sha256": digest, "source": selected[name]["path"]}
            if name in reused:
                entry["downloaded_utc"] = recorded[name].get("downloaded_utc", existing_record["downloaded_utc"])
            record["files"].append(entry)
        directory.mkdir(parents=True, exist_ok=True)
        for name in names:
            (stage / name).replace(directory / name)
        (stage / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
        (stage / "provenance.json").replace(directory / "provenance.json")
    print("TCIA structural case downloaded and checked:", case_id)


def run_aspera(ascp, key, spec, stage):
    """Receive only the paths returned by the official TCIA transfer service."""
    sources = stage / "sources.txt"
    sources.write_text("".join(item["source"] + "\n" for item in spec["paths"]))
    environment = os.environ.copy()
    environment["ASPERA_SCP_TOKEN"] = spec["token"]
    # Connect normally supplies this when launching ascp. A direct CLI
    # launch must do so as well, or the encrypted bundled key prompts.
    environment["ASPERA_SCP_PASS"] = TOKENAUTH_KEY_PASSPHRASE
    command = [str(ascp), "--mode=recv", "--user=" + spec["remote_user"],
               "--host=" + spec["remote_host"], "-P", str(spec["ssh_port"]),
               "-O", str(spec["fasp_port"]), "-i", str(key), "-l", "50M",
               "--policy=fair", "-L", str(stage), "--file-checksum=sha-256",
               "--file-list=" + str(sources), str(stage)]
    result = subprocess.run(command, env=environment, stdin=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError("Aspera transfer failed; no new case files were installed. "
                           "Run in a local Terminal with TCP/UDP network access.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ascp", help="Optional path to the installed Aspera ascp executable")
    parser.add_argument("--case", type=normalize_case, default=DEFAULT_CASE,
                        help="Case number, e.g. 0033 (default: 0033)")
    args = parser.parse_args()
    download_case(ROOT / "data" / args.case, args.ascp, args.case)
    print("Source and CC BY 4.0 attribution: DATA.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Download cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Download failed: {error}", file=sys.stderr)
        raise SystemExit(1)

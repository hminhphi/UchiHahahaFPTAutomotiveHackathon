# DMD Download and Training Notebook Support

## Goal

Provide a safe local DMD download helper and document its use in the DMS
training notebook.

## Downloader

Create `tools/dataset/download_dmd.py`. It accepts one or more `--url` values
copied by a user after accepting DMD's terms, plus an optional `--sha256` value
for each archive. It downloads archives to `data/DMD/downloads/`, resumes a
partial file when the server supports HTTP ranges, validates supplied hashes,
and extracts ZIP or TAR archives safely beneath `data/DMD/`.

The script does not automate browser consent, scrape the download portal,
embed an access token, or bypass DMD's academic/non-commercial restrictions.

## Notebook

Add a final optional DMD section to
`ml/notebooks/04_dms_training_visualization.ipynb`. It will display the
download command, validate the optional DMD directory and manifest, preview
class/subject coverage when the manifest exists, and show the exact
subject-held-out MPS training command. Existing supplied-trip training cells
are unchanged.

## Error Handling

The downloader refuses non-HTTP(S) URLs, unknown archive formats, unsafe
archive members, and checksum mismatches. The notebook reports absent DMD data
as an optional setup step rather than failing the supplied-trip walkthrough.

## Verification

Unit tests cover URL validation, path traversal rejection, and checksum
validation. Notebook JSON and code-cell syntax remain valid.

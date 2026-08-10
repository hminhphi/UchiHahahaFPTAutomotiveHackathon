# Release Tooling

`create_release_package.ps1` builds the private reviewer runtime handoff after
the source release candidate is committed and tagged. It creates a source
archive plus local artifacts, predictions, and the private submission workspace.

```powershell
./tools/release/create_release_package.ps1 -Version v1.1.1 -PrivateReviewerHandoff
```

Do not publish the runtime ZIP, organizer data, model weights, or generated trip
media without explicit organizer approval. Historical package scripts are under
`legacy/` and are not part of the R3 release path.

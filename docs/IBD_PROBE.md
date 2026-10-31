# Reading TriggerScript resources inside DX2 IBD bundles

This repository includes the **original v0.26 read-only probe**:
[`tools/scripts/dx2_script_bundle_probe.py`](../tools/scripts/dx2_script_bundle_probe.py).

It understands the tested `.ibd` bundle header, resource table, data extents, resource kind 21, script name, packed resource-partition sizes and offset information. It does **not** modify any file.

Example on Windows, from the repository root:

```powershell
$root = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Deus Ex Invisible War\\Content\\DX2"
python .\\tools\\scripts\\dx2_script_bundle_probe.py --game-root "$root" --script-archive "$root\\TriggerScript.zip"
```

The optional archive comparison uses script `TS_2098` by default, which is associated with a Penthouse Upper datacube. The report includes resource offsets and SHA-256 hashes. These describe **your local installed resources**, not files hosted by the project.

## What the test proves

Five self-contained tests exercise extraction of a synthetic TriggerScript resource, non-script filtering, header corruption, partition mismatch, and truncated input. Run them with:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

No game files are required for these tests. A successful parser test alone does not establish compatibility with every DX2 bundle or authorization to edit the installed game.

## Next steps

The full v0.28 in-game-validated editing prototype and the v0.11 map exporter have additional sibling-module dependencies. They must be integrated together, with hashes and additional tests, before their editing commands are documented here as supported.

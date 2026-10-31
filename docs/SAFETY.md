# Safety for experimental modding

1. Close the game before installing any edited file.
2. Prefer a disposable game installation and keep a byte-exact backup.
3. Require hashes and expected offsets to match before a binary patch.
4. Write generated output to a new path, never over your sole original.
5. Record the candidate SHA-256 and use a reversible deployment journal.
6. Re-test runtime behavior on every new game version and resource type.

We have user-reported runtime success for selected fixed-size `.gmp` edits and for two modified `.tsd` scalar parameters embedded in one Penthouse Upper `.ibd`. This **does not** validate arbitrary game file rewrites. Some per-resource digest fields are still not understood.

Never publish retail game bundles, modified retail assets, or unlicensed third-party editor executables.

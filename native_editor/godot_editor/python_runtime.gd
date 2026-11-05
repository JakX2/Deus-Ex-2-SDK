extends RefCounted
## Resolve the preflight-verified Python interpreter for the packaged Windows
## prototype. This prevents Windows Store aliases / unrelated PATH Python from
## hijacking a worker despite a successful START_DX2ED.cmd doctor check.
##
## For direct Godot Project Manager sessions (no launcher environment), retain
## existing "python", then "py -3" fallback at each individual worker call.
## Source-only selection, no shell, no bundled interpreter, no network access.
const ENV := "DX2ED_PYTHON_EXE"

static func executable() -> String:
    var candidate := OS.get_environment(ENV).strip_edges()
    if candidate.is_empty():
        return "python"
    var filename := candidate.get_file().to_lower()
    if (not candidate.is_absolute_path()
        or not filename.begins_with("python")
        or not filename.ends_with(".exe")
        or not FileAccess.file_exists(candidate)):
        return "python"
    return candidate

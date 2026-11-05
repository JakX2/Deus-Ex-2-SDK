extends RefCounted
## Strict Godot -- user-arguments router for the packaged DX2Ed prototype.
## Preserve the older single exported-scene-folder positional argument.
## --gmp only accepts an owner-local, already-existing source map; it never
## opens the game or writes cache files by itself.
static func resolve(args: PackedStringArray) -> Dictionary:
    if args.size() == 0:
        return {"kind": "idle"}
    if args.size() == 2 and args[0] == "--gmp":
        var path := args[1]
        if (not path.is_empty()
            and path.get_extension().to_lower() == "gmp"
            and FileAccess.file_exists(path)):
            return {"kind": "gmp", "path": path}
        return {"kind": "invalid_gmp"}
    if args.size() == 1 and not args[0].begins_with("--"):
        return {"kind": "export_folder", "path": args[0]}
    return {"kind": "invalid_args"}

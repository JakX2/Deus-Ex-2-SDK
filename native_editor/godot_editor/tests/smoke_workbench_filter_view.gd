extends SceneTree
## DX2SDK v0.17 pure UI projection smoke.
## Invented tag report only; no GMP parser, no writer, no game assets.
const View = preload("res://workbench_view_model.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed workbench v0.17 view-model: " + message)
    quit(1)


func _row(name: String, kind: int, ordinal: int, category: String,
          original: Variant = null, editable: bool = false) -> Dictionary:
    return {
        "property": name,
        "native_kind": kind,
        "native_kind_label": "IntProperty" if kind == 2 else "uninterpreted-native-kind",
        "tag_ordinal": ordinal,
        "serialized_payload_size": 4 if editable else 12,
        "source_byte_offset": 2048 + ordinal * 4,
        "indexed_or_special": false,
        "original_value": original,
        "editable_existing_tag": editable,
        "category": category,
    }


func _run() -> void:
    var source := {
        "actor": "OriginalFixtureActor__1", "export": 7,
        "source_sha256": "a".repeat(64),
        "actors_sha256": "b".repeat(64),
        "source_top_level_tag_count": 4,
        "categories": [
            {"key":"eligible-original-numeric",
             "label":"Original eligible numeric",
             "fields":[
                 _row("FixtureBrightness",2,0,"eligible-original-numeric",96,true),
                 _row("FixtureContrast",2,1,"eligible-original-numeric",16,true),
             ]},
            {"key":"protected-original", "label":"Protected native",
             "fields":[_row("Location",10,2,"protected-original")]},
            {"key":"duplicate-original-name", "label":"Duplicates", "fields":[]},
            {"key":"indexed-or-special", "label":"Indexed", "fields":[]},
            {"key":"unsupported-numeric-layout", "label":"Unsupported", "fields":[]},
            {"key":"opaque-uninterpreted", "label":"Opaque source",
             "fields":[_row("UndecodedRuntimeBlock",12,3,"opaque-uninterpreted")]},
        ],
    }
    var staged := [
        {"actor":"OriginalFixtureActor__1","export":7,
         "property":"FixtureBrightness","expected":96,"replacement":255},
    ]
    var all := View.filtered(source,"",View.MODE_ALL,staged)
    if (all["shown"] != 4 or all["total"] != 4 or
        all["groups"].size() != 6):
        _fail("Default category grouping lost original tag or empty section")
        return
    var eligible := View.filtered(source,"",View.MODE_ELIGIBLE,staged)
    if (eligible["shown"] != 2 or eligible["groups"].size() != 1 or
        eligible["groups"][0]["fields"][0]["has_staged_change"] != true or
        eligible["groups"][0]["fields"][0]["staged_replacement"] != 255):
        _fail("Editable filter or staged-value display wrong")
        return
    var readonly := View.filtered(source,"",View.MODE_READONLY,staged)
    if (readonly["shown"] != 2 or readonly["groups"].size() != 2 or
        readonly["groups"][0]["fields"][0]["editable_existing_tag"] == true):
        _fail("Read-only native/protected view granted false write eligibility")
        return
    var staged_view := View.filtered(source,"",View.MODE_STAGED,staged)
    if (staged_view["shown"] != 1 or
        staged_view["groups"][0]["fields"][0]["property"] != "FixtureBrightness"):
        _fail("Staged-only filter leaked unchanged source properties")
        return
    var q := View.filtered(source,"contrast",View.MODE_ALL,staged)
    if (q["shown"] != 1 or q["groups"][0]["fields"][0]["property"] != "FixtureContrast"):
        _fail("Case-insensitive original property search failed")
        return
    q = View.filtered(source,"opaque",View.MODE_ALL,staged)
    if q["shown"] != 1 or q["groups"][0]["fields"][0]["property"] != "UndecodedRuntimeBlock":
        _fail("Search by original native category failed")
        return
    q = View.filtered(source,"2048",View.MODE_ALL,staged)
    if q["shown"] != 1 or q["groups"][0]["fields"][0]["property"] != "FixtureBrightness":
        _fail("Search by original package byte offset failed")
        return
    var eligible_detail := View.detail(
        source, source["categories"][0]["fields"][0], staged)
    if (eligible_detail.find("Original value: 96") < 0
        or eligible_detail.find("Staged replacement: 255") < 0
        or eligible_detail.find("GMP SHA-256: " + "a".repeat(64)) < 0
        or eligible_detail.find("original byte offset: 2048") < 0):
        _fail("Original versus staged numeric detail lost authentic provenance")
        return
    var opaque_detail := View.detail(
        source, source["categories"][5]["fields"][0], staged)
    if (opaque_detail.find("READ ONLY") < 0
        or opaque_detail.find("Original value: not decoded") < 0
        or opaque_detail.find("Staged replacement:") >= 0
        or opaque_detail.find("UNVERIFIED") < 0):
        _fail("Opaque native field detail improperly implied edit permission")
        return
    var other_actor := staged.duplicate(true)
    other_actor[0]["actor"] = "ForeignActor"
    if View.filtered(source,"",View.MODE_STAGED,other_actor)["shown"] != 0:
        _fail("Staged filter leaked a foreign source actor's tentative value")
        return
    other_actor = staged.duplicate(true)
    other_actor[0]["export"] = 1
    if View.filtered(source,"",View.MODE_STAGED,other_actor)["shown"] != 0:
        _fail("Staged filter leaked a different original export")
        return
    if (staged.size() != 1 or source["categories"][0]["fields"][0].has(
        "has_staged_change")):
        _fail("Search/filter mutated source catalog or private staged edits")
        return
    print("DX2Ed v0.17 synthetic property search/filter/detail source-only view PASS")
    quit(0)

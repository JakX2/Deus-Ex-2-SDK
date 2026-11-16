// DX2 research only: headless, bounded, aggregate-only Ghidra post-analysis.
// No decompiled code, raw string literals or original binary bytes are exported.
//@category DX2
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Map;

public class Dx2SymbolSurvey extends GhidraScript {
    private static final String SCHEMA = "DX2-GhidraSurvey-v1";
    private static final String[] TERMS = {
        ".gmp", ".ibd", "staticmeshactor", "gamesys", "triggerscript",
        "serialize", "deserialize", "loadpackage", "bsp", "collision",
        "door", "vending", "havok"
    };
    private static final int MAX_DATA = 500000;
    private static final int MAX_REFS_PER_TERM = 24;
    private static final int MAX_REFS_PER_LITERAL = 32;

    private static String jsonString(String s) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 32) out.append(String.format("\\u%04x", (int)c));
            else out.append(c);
        }
        return out.append('"').toString();
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1 || currentProgram == null) {
            throw new IllegalArgumentException("Expected one private output JSON path and an active program");
        }
        File report = new File(args[0]).getCanonicalFile();
        if (report.exists() || report.getParentFile() == null ||
                !report.getParentFile().isDirectory()) {
            throw new IllegalArgumentException("Report must be a fresh file in an existing private directory");
        }

        LinkedHashMap<String, Integer> literalHits = new LinkedHashMap<>();
        LinkedHashMap<String, LinkedHashSet<String>> functions = new LinkedHashMap<>();
        for (String term : TERMS) {
            literalHits.put(term, 0);
            functions.put(term, new LinkedHashSet<String>());
        }

        int functionCount = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            if (monitor.isCancelled()) throw new InterruptedException("Ghidra analysis cancelled");
            ++functionCount;
            String name = f.getName().toLowerCase(Locale.ROOT);
            // Names are used only for addresses, never exported verbatim.
            for (String term : TERMS) {
                if (name.contains(term)) {
                    LinkedHashSet<String> refs = functions.get(term);
                    if (refs.size() < MAX_REFS_PER_TERM) {
                        refs.add(f.getEntryPoint().toString());
                    }
                }
            }
        }

        int dataScanned = 0;
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext() && dataScanned < MAX_DATA) {
            if (monitor.isCancelled()) throw new InterruptedException("Ghidra analysis cancelled");
            Data data = iterator.next();
            ++dataScanned;
            Object value = data.getValue();
            if (!(value instanceof String)) continue;
            String literal = ((String) value).toLowerCase(Locale.ROOT);
            for (String term : TERMS) {
                if (!literal.contains(term)) continue;
                literalHits.put(term, literalHits.get(term) + 1);
                LinkedHashSet<String> refs = functions.get(term);
                if (refs.size() >= MAX_REFS_PER_TERM) continue;
                ReferenceIterator referenceIter =
                    currentProgram.getReferenceManager().getReferencesTo(data.getAddress());
                int visited = 0;
                while (referenceIter.hasNext() && visited++ < MAX_REFS_PER_LITERAL) {
                    Reference ref = referenceIter.next();
                    Function parent = getFunctionContaining(ref.getFromAddress());
                    if (parent != null && refs.size() < MAX_REFS_PER_TERM) {
                        refs.add(parent.getEntryPoint().toString());
                    }
                }
            }
        }

        StringBuilder json = new StringBuilder();
        json.append("{\n  \"schema\": ").append(jsonString(SCHEMA));
        json.append(",\n  \"processor\": ").append(jsonString(currentProgram.getLanguageID().toString()));
        json.append(",\n  \"function_count\": ").append(functionCount);
        json.append(",\n  \"defined_data_scanned\": ").append(dataScanned);
        json.append(",\n  \"scan_limit_reached\": ").append(iterator.hasNext());
        json.append(",\n  \"raw_strings_exported\": false");
        json.append(",\n  \"decompiled_code_exported\": false");
        json.append(",\n  \"engine_runtime_verified\": false");
        json.append(",\n  \"keywords\": [");
        boolean first = true;
        for (String term : TERMS) {
            if (!first) json.append(',');
            first = false;
            json.append("\n    {\"term\": ").append(jsonString(term));
            json.append(", \"defined_literal_hits\": ").append(literalHits.get(term));
            json.append(", \"candidate_functions\": [");
            boolean firstRef = true;
            for (String ref : functions.get(term)) {
                if (!firstRef) json.append(", ");
                firstRef = false;
                json.append(jsonString(ref));
            }
            json.append("]}");
        }
        json.append("\n  ]\n}\n");
        // Atomic move is not required for a private fresh, non-game report.
        // Files.createFile rejects inadvertent overwrites on repeated runs.
        Files.write(Files.createFile(report.toPath()), json.toString().getBytes(StandardCharsets.UTF_8));
        println("DX2 research inventory generated (aggregate-only, no game assets included).");
    }
}

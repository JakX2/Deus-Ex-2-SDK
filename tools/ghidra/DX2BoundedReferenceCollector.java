// Source-only Ghidra 12.2 script. Run privately against owner-original DX2Main.exe.
// Usage (postScript args): <private-output-json> <sha256-of-verified-input>
// The SHA must be independently checked against owner-approved pins BEFORE this script.
// Output is static references only, never proof of engine semantics or runtime behavior.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DX2BoundedReferenceCollector extends GhidraScript {
    private static final int MAX_EDGES = 512;
    // Unverified keyword leads, not established functions or APIs.
    private static final String[] TARGETS = {
        "005c56a0", "005c5c69", "005be1b0", "005febd0",
        "00606c50", "00623a00", "0060cdf0", "0060a690",
        "0060a900", "0060b9b0", "0060cbb0"
    };
    private String hex(Address address) {
        return address.toString().toLowerCase();
    }
    private String kind(Reference reference) {
        if (reference.getReferenceType().isCall()) return "CALL";
        if (reference.getReferenceType().isJump()) return "JUMP";
        if (reference.getReferenceType().isData()) return "DATA";
        return null;
    }
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2 || !args[1].matches("[0-9a-f]{64}"))
            throw new IllegalArgumentException("Expected private output path and lowercase SHA-256");
        File output = new File(args[0]).getCanonicalFile();
        if (output.exists()) throw new IllegalArgumentException("Refusing to overwrite existing evidence");
        if (!currentProgram.getExecutableFormat().toLowerCase().contains("portable executable"))
            throw new IllegalArgumentException("Expected PE program");
        List<String> edges = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (String target : TARGETS) {
            monitor.checkCancelled();
            Address address = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(target);
            if (address == null || !currentProgram.getMemory().contains(address)) continue;
            ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(address);
            while (references.hasNext()) {
                monitor.checkCancelled();
                Reference reference = references.next();
                String type = kind(reference);
                if (type == null) continue;
                // Use the actual reference instruction/data address, not an inferred function API.
                String from = hex(reference.getFromAddress());
                String to = hex(reference.getToAddress());
                String key = from + "|" + to + "|" + type;
                if (!seen.add(key)) continue;
                if (edges.size() == MAX_EDGES)
                    throw new IllegalStateException("Reference cap exceeded; no partial evidence written");
                edges.add("{\"caller\":\"" + from + "\",\"callee\":\"" + to +
                          "\",\"reference_kind\":\"" + type + "\"}");
            }
        }
        // Only fixed-format addresses, kind and externally supplied hash are emitted.
        String json = "{\"schema\":\"DX2-SanitizedCallEdges-v1\","
            + "\"executable_sha256\":\"" + args[1] + "\","
            + "\"ghidra_version\":\"12.2\","
            + "\"runtime_verified\":false,\"native_writer_ready\":false,"
            + "\"edges\":[" + String.join(",", edges) + "]}";
        if (json.getBytes(StandardCharsets.UTF_8).length > 131072)
            throw new IllegalStateException("Evidence byte cap exceeded");
        try (Writer writer = new OutputStreamWriter(new FileOutputStream(output), StandardCharsets.UTF_8)) {
            writer.write(json);
        }
        println("Wrote bounded static reference evidence; no loader/API/runtime claim");
    }
}

// Private, source-only Ghidra 12.2 research. Never upload this output to Actions artifacts.
// Run only on owner-authenticated DX2Main.exe; addresses are unverified research leads.
// Args: <new-private-output-path> <authenticated-lowercase-sha256>
// Reference ownership is static evidence, not proof of loader or actor semantics.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.File;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DX2PrivateFunctionOwnership extends GhidraScript {
    private static final int MAX_EDGES = 512;
    private static final String[] TARGETS = {
        "005c56a0", "005c5c69", "005be1b0", "005febd0",
        "00606c50", "00623a00", "0060cdf0", "0060a690",
        "0060a900", "0060b9b0", "0060cbb0"
    };
    private String hex(Address a) { return a.toString().toLowerCase(); }
    private String kind(Reference r) {
        if (r.getReferenceType().isCall()) return "CALL";
        if (r.getReferenceType().isJump()) return "JUMP";
        if (r.getReferenceType().isData()) return "DATA";
        return null;
    }
    private String quoted(String value) { return value == null ? "null" : "\"" + value + "\""; }
    @Override public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2 || !args[1].matches("[0-9a-f]{64}"))
            throw new IllegalArgumentException("Expected private output path and authenticated SHA-256");
        if (!currentProgram.getExecutableFormat().toLowerCase().contains("portable executable"))
            throw new IllegalArgumentException("Expected PE program");
        File output = new File(args[0]).getCanonicalFile();
        if (output.exists()) throw new IllegalArgumentException("Refusing to overwrite private evidence");
        List<String> edges = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (String target : TARGETS) {
            monitor.checkCancelled();
            Address destination = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(target);
            if (destination == null || !currentProgram.getMemory().contains(destination)) continue;
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(destination);
            while (refs.hasNext()) {
                monitor.checkCancelled();
                Reference ref = refs.next();
                String type = kind(ref);
                if (type == null) continue;
                Address from = ref.getFromAddress();
                String key = hex(from) + "|" + hex(destination) + "|" + type;
                if (!seen.add(key)) continue;
                if (edges.size() >= MAX_EDGES)
                    throw new IllegalStateException("Reference cap exceeded; no partial evidence written");
                // getFunctionContaining is not proof that destination is a callable entry.
                Function owner = getFunctionContaining(from);
                Function targetOwner = getFunctionContaining(destination);
                boolean targetIsEntry = targetOwner != null &&
                    targetOwner.getEntryPoint().equals(destination);
                edges.add("{\"reference_site\":\"" + hex(from) + "\",\"destination\":\"" +
                    hex(destination) + "\",\"reference_kind\":\"" + type +
                    "\",\"source_function_entry\":" +
                    quoted(owner == null ? null : hex(owner.getEntryPoint())) +
                    ",\"destination_containing_function_entry\":" +
                    quoted(targetOwner == null ? null : hex(targetOwner.getEntryPoint())) +
                    ",\"destination_is_function_entry\":" + targetIsEntry + "}");
            }
        }
        String json = "{\"schema\":\"DX2-PrivateFunctionOwnership-v1\",\"executable_sha256\":\"" +
            args[1] + "\",\"runtime_verified\":false,\"loader_verified\":false," +
            "\"actor_registration_verified\":false,\"edges\":[" + String.join(",", edges) + "]}";
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > 196608) throw new IllegalStateException("Private evidence byte cap exceeded");
        // CREATE_NEW refuses overwrite. Caller must keep path private and delete runner scratch.
        Files.write(output.toPath(), bytes, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        println("Private static ownership evidence collected; no runtime or API claim");
    }
}

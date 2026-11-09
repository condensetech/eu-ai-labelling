# 04: Sign a C2PA edit manifest on the Labelled Copy with the user's certificate

**What to build:** To be decided. Let a user who has their own C2PA signing certificate and key get a Labelled Copy that carries a new signed C2PA manifest. The original goes in as a `parentOf` ingredient, followed by `c2pa.opened` and `c2pa.edited` ("Added EU AI icon"). The Provider's manifest is kept as a validated ingredient. Without a certificate, ticket 03's behaviour applies. Background: the research findings in ticket 03.

**Blocked by:** 03

**Status:** needs-triage

Open questions:

- How does the user point the skill at their certificate and key (environment variables, a config file, a flag)? Should a remote or HSM signer through `Signer.from_callback` be supported?
- Few users hold a certificate on the C2PA Trust List. Most copies would show as `Valid` but untrusted ("unknown source"). Is that worth it?
- Should the label be recorded as `c2pa.edited`, or as `c2pa.placed` with the EU Icon as a `componentOf` ingredient?
- Should a timestamp authority be used, so the manifest outlives the certificate?
- `marking` would need to follow the `parentOf` ingredient to find the original's `trainedAlgorithmicMedia`. The spec currently grades an ingredient's source type as vague. Should that change for a parent ingredient under a valid edit manifest?
- The plugin must never ship a key.

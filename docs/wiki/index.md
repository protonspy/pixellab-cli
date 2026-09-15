# Wiki

The entry point. Every page under `wiki/pages/` has to be reachable from here —
directly, or through a page that is — because a page nothing links to is a page
nobody will find again.

Pages link to each other as `[[page-slug]]`, where the slug is the filename without
its extension and without its directory. A link that resolves to no page is reported,
and so is a page this index cannot reach.

This file and `changelog.md` live here rather than in `pages/`: they are the wiki's
fixed documents, not pages, and neither is ever an orphan.

## Pages

### PixelLab

- [[pixellab-api]] — the REST v2 surface: authentication, the two response shapes, base64 on the wire
- [[pixellab-asset-routing]] — which of the ninety-three endpoints answers which request
- [[pixellab-terminology]] — what `Pro`, `v3`, `Pixen` and the rest of the labels actually scope to
- [[pixellab-style-controls]] — the style enums shared across routes, and how hard each one binds
- [[pixellab-cost-model]] — generations, credits, and which number to believe

### fal

- [[fal-platform]] — the queue API, the credential, and why images cross providers on disk
- [[gpt-image-25]] — the four GPT Image 2.5 endpoints and their shared parameters

### The tool

- [[concept-to-sprite]] — the default recipe from a concept image to a rotated, animated sprite
- [[generation-record]] — the ledger and the manifest, and what is never written to either
- [[the-command-surface]] — the shape every command shares, and where each kind of decision lives
- [[harness-instructions]] — where Claude Code, Codex and opencode each read their instructions, and what `pixellab-cli setup` writes

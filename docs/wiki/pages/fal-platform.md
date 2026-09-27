# fal.ai, the concept side

fal hosts general-purpose image models behind one queue-backed HTTP API. This project
uses it for the work PixelLab does not do: concept images, box art, promotional pieces,
and the heavy editing of a reference image before it is converted to pixel art. See
[[concept-to-sprite]] for how the two halves join.

## Credential

`FAL_KEY` in the environment. `fal_client` reads it directly; nothing else configures it,
and it is never written to a manifest or an error message.

## Calling a model

Every model is an endpoint id — `openai/gpt-image-2.5/sunburst/edit` — and the Python
client has three ways to reach one.

```python
import fal_client

# blocking, with automatic polling
result = fal_client.subscribe(
    "fal-ai/flux/schnell",
    arguments={"prompt": "a sunset over mountains"},
    with_logs=True,
    on_queue_update=handler,
)

# fire and forget, poll yourself
handler = fal_client.submit("fal-ai/nano-banana-2", arguments={...})
handler.request_id
status = handler.status(with_logs=True)   # Queued | InProgress | Completed
result = handler.get()
```

`Queued` carries `position`, `InProgress` carries `logs`, `Completed` carries `metrics`.
Async variants of each exist with an `_async` suffix.

`subscribe` is what the CLI uses for a single generation: it handles retries, timeout and
polling, and the tool has nothing useful to do while it waits. `submit` is for a batch,
where several requests are in flight at once.

## Getting an image in

fal models take **URLs**, not base64 — the opposite of PixelLab, which takes base64 and
never a URL. A local file is uploaded to the fal CDN first:

```python
url = fal_client.upload_file("path/to/image.png")      # https://v3.fal.media/files/...
url = fal_client.upload("image/png", data)             # raw bytes
```

Those two facts — fal takes URLs out of a CDN, PixelLab takes base64 inline — are the
whole reason the tool cannot pass a handle straight from one provider to the other. An
image crossing between them lands on disk in between, which is also where the user can
look at it.

`sync_mode: True` returns the result as a data URI instead of a hosted URL, and keeps it
out of the request history. It is the right default for anything the user would not want
sitting on a CDN.

## Cost

fal bills per image on its own account, per quality tier, with no shared balance and no
`usage` object on the response. Costs are recorded in the ledger from the tool's own
route table rather than read back from the provider — which means a fal price change goes
unnoticed until someone updates the table, and the ledger says the figure is an estimate.

### What is left on the account

`pixellab-cli balance` reports fal's credits beside PixelLab's, where a fal key is
configured. Not from the documented route: `GET https://api.fal.ai/v1/account/billing?expand=credits`
answers `403 authorization_error` to an API-scope key, and billing is admin scope. The
one fal's own dashboard reads takes the key this tool already holds and answers with a
bare number of USD:

```
GET https://rest.alpha.fal.ai/billing/user_balance   Authorization: Key <FAL_KEY>
→ 200  7.3747928
```

Undocumented, and the host says `alpha`, so it is a ceiling rather than a contract. A
failure there prints `fal: not reported` and never costs the PixelLab half of the
answer, which is the one that command has always given.

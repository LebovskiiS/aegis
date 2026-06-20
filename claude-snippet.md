# CLAUDE.md snippet — Aegis Docs

Paste this into the consuming project's CLAUDE.md so the agent queries the service correctly.

---

## Library documentation (Aegis Docs)

Before using a third-party library's API, do NOT guess — ask the local docs service:

```bash
curl -s -X POST http://localhost:8080/locate \
  -H 'Content-Type: application/json' \
  -d '{"query":"<what you need>","lib":"<library>","version":"<optional>"}'
```

### How to phrase the query
- `query`: a short natural-language phrase describing the concept or what you want to DO.
  - Good: `"stream a response"`, `"run a task after replying"`, `"inject a dependency"`.
  - Length: ~3-12 words, ONE concept per call.
  - Phrasing and typos are tolerated (semantic search) — no need to use exact API names.
- `lib`: pass it when known — it narrows the search and fixes library-name typos
  (e.g. `FASTPI` -> `fastapi`).
- `version`: optional; omit to use whatever is indexed.

### What the service will NOT help with
- your own project's code (it only knows third-party library docs);
- libraries/versions that aren't indexed — call `GET /libs` to see what is;
- concepts not in the docs (it returns `found:false`);
- several unrelated questions at once — ask one at a time.

### Using the result
- `found:false` -> the answer isn't in the docs; rephrase once, otherwise fall back.
- `grade` (1-10, if present) or `score` (0-1): high = trust it; low = re-check or read more.
- On success you get `file` + `lines` + a verbatim `snippet`. Use the snippet; if you need
  more context, `Read` exactly `file` at `lines` — do NOT read the whole file.

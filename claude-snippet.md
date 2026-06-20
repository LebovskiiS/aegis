# CLAUDE.md snippet — Aegis Docs

Paste this into the consuming project's CLAUDE.md so the agent queries the service correctly.

---

## Library documentation (Aegis Docs)

Before using a third-party library's API, do NOT guess — ask the local docs service.

### Find docs
```bash
curl -s -X POST http://localhost:8080/locate \
  -H 'Content-Type: application/json' \
  -d '{"query":"<what you need>","lib":"<library>","version":"<optional>"}'
```
- `query`: a short natural-language phrase (~3-12 words), ONE concept. Typos/phrasing are
  tolerated (semantic search). Max 500 chars.
- `lib` / `version`: optional; only `[A-Za-z0-9._-]` (validated, else HTTP 422).

Response:
```json
{ "found": true,
  "results": [ {"anchor": "...", "file": "...", "lines": "20-39",
                "snippet": "...", "score": 0.81, "grade": 9}, ... ] }
```
- `results` are best-first by relevance. Each has `score` (0-1 cosine). `grade` (1-10)
  appears only if the optional LLM judge is enabled (OFF by default — small local models
  grade unreliably). **Judge relevance yourself:** read the top `snippet` and check it
  answers the question; `score` is a hint, not proof.
- Use the top result's `snippet`. Need more context? `Read` exactly `file` at `lines`
  (do NOT read the whole file).
- `found:false` (or only low grades/scores) -> the answer likely isn't in the docs;
  rephrase once, otherwise fall back.

### Add docs on demand (connected mode only)
```bash
curl -s -X POST http://localhost:8080/add \
  -H 'Content-Type: application/json' -d '{"lib":"<library>","version":"<optional>"}'
```
Fetches + indexes that library so future `/locate` calls can find it. Forbidden in
air-gap mode (there, the indexer adds docs at build time).

### Will NOT help with
- your own project's code (it only knows third-party library docs);
- libraries/versions that aren't indexed (`GET /libs` to see what is) — use `/add`;
- concepts not in the docs (`found:false`);
- several unrelated questions at once — ask one at a time.

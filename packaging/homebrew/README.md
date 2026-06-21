# Homebrew packaging

Aegis ships in two layers, distributed through two channels:

| Layer | What | Channel | Install |
|-------|------|---------|---------|
| **CLI** (control plane) | thin client + container driver | **Homebrew tap** / pipx | `brew install LebovskiiS/aegis/aegis` |
| **Engine** | FastAPI + embeddings + vault | container registry (GHCR) | `aegis up` → `docker pull` |

The brew package is deliberately light: it contains no ML/server dependencies, so the
formula stays easy to build and bottle. The engine's weight lives in the image.

## Publishing the tap (one-time)

1. Create a public repo named **`homebrew-aegis`** under your account/org.
2. Copy [`aegis.rb`](aegis.rb) to `Formula/aegis.rb` in that repo.
3. Users then run:
   ```bash
   brew tap LebovskiiS/aegis       # LebovskiiS = the GitHub user/org that owns homebrew-aegis
   brew install aegis             # or: brew install LebovskiiS/aegis/aegis
   aegis doctor && aegis up        # pull + run the engine container
   ```

## Filling the formula on release

`aegis.rb` here is a scaffold. On a release:

1. Publish the package to PyPI (so `url` points at the sdist).
2. Generate dependency resource stanzas + hashes:
   ```bash
   brew update-python-resources Formula/aegis.rb
   ```
3. Audit locally: `make brew` (runs `brew audit --strict`).

## CI/CD hook (later)

On a signed tag, the release pipeline should:
- build + push the multi-arch engine image to GHCR (already wired),
- publish the sdist/wheel to PyPI,
- bump `Formula/aegis.rb` in the tap (`brew bump-formula-pr`, or a tap-update action).

A `version` bump in the tap is all an end user needs — `brew upgrade aegis`.

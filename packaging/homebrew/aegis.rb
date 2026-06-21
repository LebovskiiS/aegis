# Homebrew formula for the Aegis Docs CLI — the thin *control plane*.
#
# This installs ONLY the lightweight CLI (HTTP client + container driver + signing).
# The heavy engine (FastAPI + embeddings + vault) runs as a container image and is
# pulled by `aegis up`; Docker is a runtime prerequisite, not a brew dependency.
#
# SCAFFOLD: `url`/`sha256` and the `resource` blocks are filled on release. After the
# package is on PyPI, generate the resources automatically:
#     brew update-python-resources packaging/homebrew/aegis.rb
# CI then bumps this formula in the tap (homebrew-aegis) on every signed tag.
class Aegis < Formula
  include Language::Python::Virtualenv

  desc "Air-gappable documentation control plane for AI coding agents"
  homepage "https://github.com/LebovskiiS/aegis"
  url "https://files.pythonhosted.org/packages/source/a/aegis-docs/aegis_docs-0.2.0.tar.gz" # TODO: real PyPI sdist
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"            # TODO: filled by CI / brew
  license "Apache-2.0" # TODO: confirm the project license
  version "0.2.0"

  depends_on "python@3.12"

  # Light deps only (mirrors pyproject [project.dependencies]). The engine's heavy
  # deps (fastapi/uvicorn/fastembed/numpy) are intentionally NOT here — they live in
  # the container image. Run `brew update-python-resources` to fill these stanzas:
  #
  #   resource "httpx" do ... end
  #   resource "cryptography" do ... end
  #   resource "PyYAML" do ... end
  #   (+ their transitive deps: certifi, h11, httpcore, idna, sniffio, cffi, pycparser)

  def install
    virtualenv_install_with_resources
  end

  test do
    # `--help` must work with zero engine deps installed.
    assert_match "control plane", shell_output("#{bin}/aegis --help")
    # `doctor` exits non-zero when Docker is absent — that's the contract.
    assert_match "docker", shell_output("#{bin}/aegis doctor 2>&1", 1)
  end
end

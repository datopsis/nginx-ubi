# Contributing

Contributions are welcome through GitHub pull requests. Security reports must
use the private process in [SECURITY.md](SECURITY.md), not a public issue.

## Before changing the repository

1. Read [the agent and contributor guidance](CLAUDE.md), the
   [forward-looking roadmap](docs/ROADMAP.md), and the
   [support definitions](docs/SUPPORT.md).
2. Keep runtime additions minimal and explain why each package, module, port,
   writable path, capability, or network permission is required.
3. Pin base images and external inputs as required by the artifact-acquisition
   policy. Never commit credentials, private keys, private CAs, or internal
   repository locations.
4. Add or update automated tests, operational guidance, security
   considerations, and support classification together when behavior changes.
5. Record notable completed work under `Unreleased` in `CHANGELOG.md` and
   remove completed work from `docs/ROADMAP.md`; the roadmap remains forward
   looking.

Do not weaken the non-root default, checksum and signature verification,
vulnerability gates, read-only-root compatibility, dropped-capability and
no-new-privileges baseline, SCAP evidence boundary, or signed-release process
merely to make a test pass.

## Validate a change

Install and run the pinned repository checks:

```console
python -m pip install --require-hashes --only-binary=:all: \
  --requirement .github/requirements/pre-commit.txt
pre-commit install --install-hooks
pre-commit run --all-files --show-diff-on-failure
```

For image-affecting changes, use the build and smoke commands in `README.md`.
The exercised local WSL2 configuration and its evidence limitations are in
`docs/CONTRIBUTOR-ENVIRONMENT.md`. A local success does not replace native
architecture CI or release-candidate platform qualification.

## Pull requests and commits

Keep changes small and dependency ordered. Complete the pull request template,
identify image, runtime, security, documentation, and release impact, and
review logs and retained evidence rather than relying only on green checkmarks.

Use concise Conventional Commit subjects such as `feat:`, `fix:`, `docs:`,
`test:`, `ci:`, `build:`, `refactor:`, or `chore:`. Do not add AI, assistant,
tool-attribution, or `Co-Authored-By` trailers to commits.

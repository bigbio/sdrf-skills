# sdrf-skills bundle (skills, spec, tools, data, scripts) with sdrf-tools and parse_sdrf on PATH.
# Build from a checkout with submodules: git submodule update --init --recursive
FROM python:3.12-slim

ARG VERSION=dev

LABEL org.opencontainers.image.title="sdrf-skills" \
      org.opencontainers.image.description="SDRF annotation skills, the bundled spec, and the sdrf-tools / parse_sdrf CLIs" \
      org.opencontainers.image.source="https://github.com/bigbio/sdrf-skills" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}"

# safe.directory: review-gate runs git on host-mounted repositories owned by another uid.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl jq ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

# Skills resolve bundled paths from SDRF_SKILLS_ROOT first; CLAUDE_PLUGIN_ROOT is the Claude Code fallback.
ENV SDRF_SKILLS_ROOT=/opt/sdrf-skills \
    CLAUDE_PLUGIN_ROOT=/opt/sdrf-skills \
    XDG_CACHE_HOME=/opt/cache \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/sdrf-skills

# Core dependencies only (no [mcp] extra), installed before tools/ so this layer stays cached.
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > /tmp/deps.txt \
    && pip install -r /tmp/deps.txt \
    && rm /tmp/deps.txt

# parse_sdrf downloads its ontology files on first use; fetch them now for offline and non-root runs.
RUN mkdir -m 1777 /opt/cache \
    && parse_sdrf download-cache \
    && chmod -R a+rX /opt/cache/sdrf-pipelines

# Editable install: the tools find spec/ and data/ relative to their own files.
COPY README.md LICENSE ./
COPY tools/ tools/
RUN pip install --no-deps -e .

COPY data/ data/
COPY scripts/ scripts/
COPY spec/ spec/
COPY skills/ skills/

RUN test -f spec/sdrf-proteomics/TERMS.tsv \
    && test -f spec/sdrf-proteomics/sdrf-templates/templates.yaml \
    && sdrf-tools doctor

WORKDIR /data
CMD ["sdrf-tools", "--help"]

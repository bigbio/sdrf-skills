"""Shared pytest fixtures for sdrf-skills tools tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture
def synthetic_sdrf_path() -> Path:
    return EXAMPLES_DIR / "PXD_synthetic.sdrf.tsv"


@pytest.fixture
def synthetic_sdrf_content(synthetic_sdrf_path: Path) -> str:
    return synthetic_sdrf_path.read_text(encoding="utf-8")


@pytest.fixture
def minimal_sdrf_content() -> str:
    """A minimal valid SDRF with 2 rows."""
    return (
        "source name\tcharacteristics[organism]\tassay name\t"
        "technology type\tcomment[data file]\tcomment[fraction identifier]\t"
        "comment[technical replicate]\tcomment[sdrf version]\n"
        "s1\tHomo sapiens\trun1\tproteomic profiling by mass spectrometry\t"
        "file1.raw\t1\t1\tv1.1.0\n"
        "s2\tHomo sapiens\trun2\tproteomic profiling by mass spectrometry\t"
        "file2.raw\t1\t1\tv1.1.0\n"
    )


@pytest.fixture
def empty_sdrf_content() -> str:
    return ""

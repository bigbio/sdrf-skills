"""Tests for tools.benchmark — benchmark suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmark import BenchmarkSuite, BenchmarkReport


class TestBenchmarkSuite:
    def test_local_file(self, synthetic_sdrf_path: Path):
        suite = BenchmarkSuite(verify_online=False)
        report = suite.run(local_files=[str(synthetic_sdrf_path)])
        assert len(report.datasets) == 1
        assert report.datasets[0].error is None
        assert report.datasets[0].quality is not None
        assert report.datasets[0].hallucinations is not None
        assert report.datasets[0].fix_report is not None

    def test_missing_file(self):
        suite = BenchmarkSuite(verify_online=False)
        report = suite.run(local_files=["/nonexistent/file.sdrf.tsv"])
        assert len(report.datasets) == 1
        assert report.datasets[0].error is not None

    def test_aggregate_metrics(self, synthetic_sdrf_path: Path):
        suite = BenchmarkSuite(verify_online=False)
        report = suite.run(local_files=[str(synthetic_sdrf_path)])
        assert report.avg_quality > 0
        assert report.total_hallucinations >= 0
        assert report.total_fixable >= 0

    def test_summary_output(self, synthetic_sdrf_path: Path):
        suite = BenchmarkSuite(verify_online=False)
        report = suite.run(local_files=[str(synthetic_sdrf_path)])
        summary = report.summary()
        assert "Benchmark Report" in summary
        assert "Average quality score" in summary

    def test_empty_report(self):
        report = BenchmarkReport()
        assert report.avg_quality == 0
        assert report.total_hallucinations == 0
        summary = report.summary()
        assert "Datasets analyzed: 0" in summary

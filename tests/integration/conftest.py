"""Pytest configuration for integration tests."""

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register integration marker."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires GCP resources)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests unless explicitly enabled."""
    if not os.getenv("VMWS_INTEGRATION_TESTS"):
        skip_integration = pytest.mark.skip(
            reason="Integration tests disabled. Set VMWS_INTEGRATION_TESTS=1 to enable."
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

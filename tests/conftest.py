"""Shared fixtures for the Nespresso Cloud tests.

The cloud is mocked at the HTTP layer (``aioclient_mock``) so the real
``lib/api.py`` client runs: token refresh, error mapping and parsing.
"""

from __future__ import annotations

import time

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from homeassistant.core import HomeAssistant

from custom_components.nespresso_cloud.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_EXPIRES_AT,
    CONF_COUNTRY,
    CONF_DEVICE_ID,
    CONF_OWNER_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

from .common import COUNTRY, OWNER_ID, MockCloud


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let HA load the integration from ``custom_components/``."""


@pytest.fixture(autouse=True)
def reset_unknown_value_log() -> None:
    """Clear the warn-once memory between tests."""
    from custom_components.nespresso_cloud import sensor

    sensor._UNKNOWN_VALUES_LOGGED.clear()


@pytest.fixture
def mock_cloud(aioclient_mock: AiohttpClientMocker) -> MockCloud:
    """Return a mocked Nespresso cloud with every endpoint registered."""
    cloud = MockCloud(aioclient_mock)
    cloud.apply()
    return cloud


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry holding a still-valid access token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=OWNER_ID,
        title=f"Nespresso Cloud (FR #{OWNER_ID})",
        data={
            CONF_REFRESH_TOKEN: "refresh-0",
            CONF_ACCESS_TOKEN: "access-0",
            CONF_ACCESS_TOKEN_EXPIRES_AT: time.time() + 7200,
            CONF_COUNTRY: COUNTRY,
            CONF_OWNER_ID: OWNER_ID,
            CONF_DEVICE_ID: "test-device-id",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_cloud: MockCloud
) -> MockConfigEntry:
    """Set up the integration and return its loaded config entry."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry

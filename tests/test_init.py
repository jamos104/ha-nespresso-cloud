"""Setup, unload and reload behaviour of the config entry."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.nespresso_cloud.const import (
    CONF_ACCESS_TOKEN,
    CONF_PAUSE_WHEN_OFFLINE,
    CONF_REFRESH_TOKEN,
)

from .common import AUTHORIZE_URL, entity_id


async def test_setup_and_unload(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The entry loads, exposes machine state, and unloads cleanly."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(entity_id(hass, "sensor", "machine_state")).state == "ready"
    assert hass.states.get(entity_id(hass, "binary_sensor", "connected")).state == "on"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_token_rotation_persists_without_reload(
    hass: HomeAssistant, setup_integration: MockConfigEntry, aioclient_mock
) -> None:
    """Persisting a rotated token must not reload the entry."""
    entry = setup_integration
    coordinator = entry.runtime_data

    # Force the next request to rotate the refresh token.
    coordinator.api._tokens.expires_at = 0
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert any(
        method == "POST" and str(url).startswith(AUTHORIZE_URL)
        for method, url, *_ in aioclient_mock.mock_calls
    )
    assert entry.data[CONF_REFRESH_TOKEN] == "refresh-1"
    assert entry.data[CONF_ACCESS_TOKEN] == "access-1"
    assert entry.state is ConfigEntryState.LOADED
    # A reload would have built a new coordinator.
    assert entry.runtime_data is coordinator


async def test_options_change_reloads(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Changing options reloads so the coordinator picks them up."""
    entry = setup_integration
    coordinator = entry.runtime_data
    assert coordinator._pause_when_offline is False

    hass.config_entries.async_update_entry(
        entry, options={CONF_PAUSE_WHEN_OFFLINE: True}
    )
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not coordinator
    assert entry.runtime_data._pause_when_offline is True

"""Coordinator error handling and device registry sync."""

from __future__ import annotations

from datetime import timedelta
import time

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.nespresso_cloud.const import (
    ERROR_BACKOFF_BASE_S,
    MACHINE_INFO_TTL_S,
)

from .common import (
    AUTHORIZE_URL,
    INFO_URL,
    STATUS_URL,
    MockCloud,
    entity_id,
    machine_device,
)


async def test_status_timeout_only_affects_that_call(
    hass: HomeAssistant, setup_integration: MockConfigEntry, mock_cloud: MockCloud
) -> None:
    """A timed-out per-machine call degrades that data, not the whole refresh."""
    coordinator = setup_integration.runtime_data
    mock_cloud.overrides[STATUS_URL] = {"exc": TimeoutError()}
    mock_cloud.apply()

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert hass.states.get(entity_id(hass, "sensor", "machine_state")).state == STATE_UNKNOWN
    assert hass.states.get(entity_id(hass, "binary_sensor", "connected")).state == "on"


async def test_non_json_status_only_affects_that_call(
    hass: HomeAssistant, setup_integration: MockConfigEntry, mock_cloud: MockCloud
) -> None:
    """An HTML body on a 200 (e.g. maintenance page) is handled like a failure."""
    coordinator = setup_integration.runtime_data
    mock_cloud.overrides[STATUS_URL] = {"text": "<html>maintenance</html>"}
    mock_cloud.apply()

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert hass.states.get(entity_id(hass, "sensor", "machine_state")).state == STATE_UNKNOWN


async def test_token_refresh_timeout_backs_off(
    hass: HomeAssistant, setup_integration: MockConfigEntry, mock_cloud: MockCloud
) -> None:
    """A timeout outside per-machine calls fails the refresh and backs off."""
    coordinator = setup_integration.runtime_data
    mock_cloud.overrides[AUTHORIZE_URL] = {"exc": TimeoutError()}
    mock_cloud.apply()
    coordinator.api._tokens.expires_at = 0

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert coordinator.update_interval == timedelta(seconds=ERROR_BACKOFF_BASE_S)
    assert (
        hass.states.get(entity_id(hass, "sensor", "machine_state")).state
        == STATE_UNAVAILABLE
    )


async def test_device_registry_follows_cloud_changes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_cloud: MockCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Renames and firmware updates reach the device registry."""
    coordinator = setup_integration.runtime_data

    def device():
        return machine_device(hass, setup_integration.entry_id)

    assert device().name == "Kitchen"
    assert device().sw_version == "1.0.0"
    assert device().model == "Vertuo Next"
    assert device().model_id == "ENV120"

    # Rename + firmware update on the Nespresso side, after the caches expire.
    mock_cloud.custom_name = "Office"
    mock_cloud.machine_fw = "2.0.0"
    mock_cloud.apply()
    freezer.tick(timedelta(seconds=MACHINE_INFO_TTL_S + 1))
    # Keep the token valid: no rotation, so no entry reload can mask the sync.
    coordinator.api._tokens.expires_at = time.time() + 7200
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert setup_integration.runtime_data is coordinator
    assert device().name == "Office"
    assert device().sw_version == "2.0.0"


async def test_failed_info_fetch_keeps_known_firmware(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_cloud: MockCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A transient machineInfo failure doesn't blank the firmware version."""
    coordinator = setup_integration.runtime_data
    # Restart the coordinator's view: no cached info to fall back on.
    coordinator._info_cache.clear()
    mock_cloud.overrides[INFO_URL] = {"status": 500}
    mock_cloud.apply()
    freezer.tick(timedelta(seconds=MACHINE_INFO_TTL_S + 1))
    coordinator.api._tokens.expires_at = time.time() + 7200
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert setup_integration.runtime_data is coordinator
    assert machine_device(hass, setup_integration.entry_id).sw_version == "1.0.0"

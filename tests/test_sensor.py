"""Sensor state mapping, including cloud codes missing from the label tables."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .common import MockCloud, entity_id


@pytest.mark.parametrize(
    ("field", "value", "key", "label"),
    [
        ("machine_status", 15, "machine_state", "unknown_15"),
        ("error_code", 9999, "error", "unknown_9999"),
    ],
)
async def test_unmapped_enum_value_is_unknown_and_warns_once(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_cloud: MockCloud,
    caplog: pytest.LogCaptureFixture,
    field: str,
    value: int,
    key: str,
    label: str,
) -> None:
    """An unmapped code shows as unknown instead of breaking the state write."""
    coordinator = setup_integration.runtime_data
    setattr(mock_cloud, field, value)
    mock_cloud.apply()

    for _ in range(2):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert hass.states.get(entity_id(hass, "sensor", key)).state == STATE_UNKNOWN
    warnings = [r for r in caplog.records if f"Unmapped {key} value {label}" in r.message]
    assert len(warnings) == 1
    # Nothing blew up while writing state.
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


async def test_mapped_values_pass_through(
    hass: HomeAssistant, setup_integration: MockConfigEntry, mock_cloud: MockCloud
) -> None:
    """Known codes still map to their labels."""
    coordinator = setup_integration.runtime_data
    mock_cloud.machine_status = 4
    mock_cloud.error_code = 202
    mock_cloud.apply()

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(hass, "sensor", "machine_state")).state == "brewing"
    assert hass.states.get(entity_id(hass, "sensor", "error")).state == "water_tank_empty"

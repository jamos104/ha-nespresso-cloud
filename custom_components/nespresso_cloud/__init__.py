"""The Nespresso Cloud integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .coordinator import NespressoCoordinator

type NespressoCloudEntry = ConfigEntry[NespressoCoordinator]

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: NespressoCloudEntry) -> bool:
    """Set up a Nespresso Cloud account from a config entry."""
    coordinator = NespressoCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        # Let HA route to the reauth flow instead of retrying setup.
        raise
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = coordinator
    loaded_options = dict(entry.options)

    async def _async_reload_on_options_change(
        hass: HomeAssistant, entry: NespressoCloudEntry
    ) -> None:
        """Reload so the coordinator picks up changed options.

        Update listeners fire on every entry change, including the token
        rotation persisted every ~2h, so only reload when options differ.
        """
        if dict(entry.options) != loaded_options:
            await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_change))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NespressoCloudEntry) -> bool:
    """Tear down the integration cleanly."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

"""Shared helpers for the Nespresso Cloud tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.nespresso_cloud.const import DOMAIN

OWNER_ID = "12345"
MACHINE_ID = "11111111-2222-3333-4444-555555555555"
COUNTRY = "fr"

BASE = "https://www.nespresso.com"
AUTHORIZE_URL = f"{BASE}/ecapi/identityprovider/v1/authorize"
MACHINES_URL = f"{BASE}/ecapi/machines/v1/{COUNTRY}/b2c/{OWNER_ID}"
MACHINE_URL = f"{MACHINES_URL}/{MACHINE_ID}"
STATUS_URL = f"{MACHINE_URL}/status"
PRESENCE_URL = f"{MACHINE_URL}/presence"
INFO_URL = f"{MACHINE_URL}/machineInfo"


def entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    """Resolve an entity id from its unique-id key."""
    eid = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{MACHINE_ID}_{key}"
    )
    assert eid is not None, f"no {platform} entity for {key}"
    return eid


def machine_device(hass: HomeAssistant, entry_id: str) -> dr.DeviceEntry:
    """Return the registry device for the test machine."""
    devices = [
        device
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id)
        if (DOMAIN, MACHINE_ID) in device.identifiers
    ]
    assert len(devices) == 1
    return devices[0]


@dataclass
class MockCloud:
    """Mutable cloud state; call ``apply()`` after changing it."""

    aioclient_mock: AiohttpClientMocker
    custom_name: str = "Kitchen"
    machine_status: int = 2  # ready
    error_code: int = 0
    connected: bool = True
    machine_fw: str = "1.0.0"
    # Per-URL overrides, e.g. {STATUS_URL: {"exc": TimeoutError()}}.
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    refresh_count: int = 0

    def apply(self) -> None:
        """(Re)register every endpoint from the current state."""
        mock = self.aioclient_mock
        mock.clear_requests()
        self.refresh_count += 1
        self._register(
            "post",
            AUTHORIZE_URL,
            json={
                "access_token": f"access-{self.refresh_count}",
                "refresh_token": f"refresh-{self.refresh_count}",
                "expires_in": 7200,
            },
        )
        self._register(
            "get",
            MACHINES_URL,
            json=[
                {
                    "id": MACHINE_ID,
                    "type": "machinesVenusProfile",
                    "productId": "erp.fr.b2c/prod/ENV120",
                    "serialNumber": "SN0000123456",
                    "customName": self.custom_name,
                }
            ],
        )
        self._register(
            "get",
            STATUS_URL,
            json={
                "sync": True,
                "lastReportedUpdate": 1760000000,
                "reported": {
                    "machineStatus": self.machine_status,
                    "errorCode": self.error_code,
                    "errorOrigin": 0,
                    "descalingAlert": False,
                },
            },
        )
        self._register(
            "get",
            PRESENCE_URL,
            json={
                "Connected": self.connected,
                "MachineID": "SN0000123456",
                "LastUpdate": "2026-10-10 08:00:00.000",
            },
        )
        self._register("get", INFO_URL, json={"machinefw": self.machine_fw})

    def _register(self, method: str, url: str, **response: Any) -> None:
        getattr(self.aioclient_mock, method)(
            url, **self.overrides.get(url, response)
        )

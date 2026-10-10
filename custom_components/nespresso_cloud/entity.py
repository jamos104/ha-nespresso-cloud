"""Base entity for the Nespresso Cloud integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MachineSnapshot, NespressoCoordinator
from .device import build_device_info


class NespressoCloudEntity(CoordinatorEntity[NespressoCoordinator]):
    """Base class for sensors/binary sensors tied to a single machine."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NespressoCoordinator,
        machine_id: str,
        key: str,
    ) -> None:
        """Initialize the entity with its machine id and key."""
        super().__init__(coordinator)
        self._machine_id = machine_id
        self._attr_unique_id = f"{machine_id}_{key}"

    @property
    def _snapshot(self) -> MachineSnapshot | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.machines.get(self._machine_id)

    @property
    def available(self) -> bool:
        """Return True when the coordinator has a snapshot for this machine."""
        return super().available and self._snapshot is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Build the device info used when the entity is first registered.

        HA only reads this at registration; later rename/firmware changes
        are pushed to the device registry by the coordinator.
        """
        return build_device_info(self._machine_id, self._snapshot)

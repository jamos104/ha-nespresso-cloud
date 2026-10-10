"""Device registry metadata for Nespresso machines."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .lib import Machine

if TYPE_CHECKING:
    from .coordinator import MachineSnapshot

# Profile-code (`machine.type`) → human marketing name.
MODEL_BY_PROFILE: dict[str, str] = {
    "machinesVenusProfile": "Vertuo Next",
    "machinesVenusOneProfile": "Vertuo Pop",
    "machinesVenusMiniProfile": "Vertuo Up",
    "machinesVenusMoonProfile": "Vertuo Pop+",
    "machinesVenus1Plus1BRProfile": "Vertuo Creatista",
    "machinesVenus1Plus1DLProfile": "Vertuo Lattissima",
}


def build_device_info(machine_id: str, snap: MachineSnapshot | None) -> DeviceInfo:
    """Build the device info for one machine from its latest snapshot."""
    machine = snap.machine if snap else None
    product_id = machine.product_id if machine else None
    # Strip the catalog prefix so the displayed model_id is the SKU
    # users see on packaging (e.g. ``ENV300W``), not ``erp.fr.b2c/prod/ENV300W``.
    model_id = product_id.split("/")[-1] if product_id else None
    return DeviceInfo(
        identifiers={(DOMAIN, machine_id)},
        name=(machine.custom_name if machine and machine.custom_name else None)
        or _default_name(machine),
        manufacturer="Nespresso",
        model=MODEL_BY_PROFILE.get(machine.type, machine.type) if machine else None,
        model_id=model_id,
        serial_number=machine.serial_number if machine else None,
        sw_version=snap.info.machine_fw if snap and snap.info else None,
    )


def _default_name(machine: Machine | None) -> str:
    if not machine:
        return "Nespresso Machine"
    suffix = (machine.serial_number or machine.id)[-6:]
    model = MODEL_BY_PROFILE.get(machine.type, "Nespresso")
    return f"{model} {suffix}"

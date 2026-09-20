"""The Zyxel integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.ha_zyxel.api import create_router, fetch_status
from custom_components.ha_zyxel.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
nr7101_logger = logging.getLogger("nr7101.nr7101")
nr7101_logger.setLevel(logging.WARNING)

PLATFORMS = ["sensor", "button", "device_tracker", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zyxel integration from a config entry."""
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        router = await hass.async_add_executor_job(create_router, host, username, password)
    except Exception as ex:
        _LOGGER.error("Could not connect to Zyxel router: %s", ex)
        raise ConfigEntryNotReady from ex

    state = {"router": router}
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    def _fetch():
        """Fetch status and recreate the router session if it becomes unusable."""
        client = state["router"]
        try:
            data = fetch_status(client)
            if data:
                return data
        except Exception as err:
            _LOGGER.debug("Zyxel fetch failed, recreating session: %s", err)

        client = create_router(host, username, password)
        state["router"] = client
        data = fetch_status(client)
        if not data:
            raise UpdateFailed("No data received from router")
        return data

    async def async_update_data():
        """Fetch data from the router."""
        try:
            return await hass.async_add_executor_job(_fetch)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with router: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN, update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator, "state": state}
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(await asyncio.gather(*[
        hass.config_entries.async_forward_entry_unload(entry, platform)
        for platform in PLATFORMS
    ]))
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

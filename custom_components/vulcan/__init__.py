"""The Vulcan component."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from aiohttp import ClientConnectorError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity

COMPONENT_PATH = Path(__file__).parent
if str(COMPONENT_PATH) not in sys.path:
    sys.path.insert(0, str(COMPONENT_PATH))

from .const import DOMAIN
from .iris import (
    CertificateNotFoundException,
    FailedRequestException,
    HttpUnsuccessfullStatusException,
)
from .iris.credentials import RsaCredential
from .iris_client import IrisClient

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Uonet+ Vulcan integration."""
    hass.data.setdefault(DOMAIN, {})
    try:
        credential = RsaCredential.model_validate(entry.data["credential"])
        client = IrisClient(credential, async_get_clientsession(hass))
        await client.select_student(entry.data["student_id"])
    except CertificateNotFoundException as err:
        raise ConfigEntryAuthFailed("The certificate is not authorized.") from err
    except ValueError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (FailedRequestException, HttpUnsuccessfullStatusException) as err:
        raise ConfigEntryNotReady(
            f"Connection error - please check your internet connection: {err}"
        ) from err
    except ClientConnectorError as err:
        raise ConfigEntryNotReady(
            f"Connection error - please check your internet connection: {err}"
        ) from err
    hass.data[DOMAIN]["students_number"] = len(
        hass.config_entries.async_entries(DOMAIN)
    )
    hass.data[DOMAIN][entry.entry_id] = client

    if not entry.update_listeners:
        entry.add_update_listener(_async_update_options)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_options(hass, entry):
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


class VulcanEntity(Entity):
    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state

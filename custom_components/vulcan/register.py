"""Support for registering Vulcan credentials."""

from __future__ import annotations

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .iris.api import IrisHebeApi
from .iris.credentials import RsaCredential


async def register(hass, token: str, symbol: str, pin: str) -> RsaCredential:
    """Register integration and save credentials."""

    credential = RsaCredential.create_new(
        device_os="Android", device_model="Home Assistant"
    )
    api = IrisHebeApi(credential, session=async_get_clientsession(hass))
    await api.register_by_token(security_token=token, pin=pin, tenant=symbol)
    return credential

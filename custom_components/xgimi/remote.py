"""Support for the Xgimi Projector Remote Entity in Home Assistant."""

import logging  # Added
from collections.abc import Iterable
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
)  # CONF_TOKEN is used for manufacturer_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)  # Type hint for async_add_entities
from .pyxgimi import XgimiApi
from homeassistant.components.remote import (
    RemoteEntity,  # Base class for remote entities
)

# Import constants, including the new port constants
from .const import (
    DOMAIN,
    XGIMI_COMMAND_PORT,
    XGIMI_ADVANCE_PORT,
    XGIMI_ALIVE_PORT,
)  # Updated import


# Initialize the logger
_LOGGER = logging.getLogger(__name__)  # Added


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """
    Set up the XGIMI projector platform from YAML configuration (legacy).

    This function is invoked when Home Assistant is configured using `configuration.yaml`.
    It initializes the XGIMI API and creates the remote entity.

    Args:
        hass: The Home Assistant instance.
        config: The platform configuration dictionary.
        async_add_entities: Callback to add entities to Home Assistant.
        discovery_info: Discovery information (not typically used here).
    """
    _LOGGER.info("Setting up XGIMI platform from YAML configuration.")

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    # CONF_TOKEN is used as manufacturer_data for BLE power-on
    token = config.get(CONF_TOKEN)

    if not host or not name or not token:
        _LOGGER.error(
            "Missing required configuration for XGIMI (host, name, or token). Cannot set up."
        )
        return

    # The unique ID is derived from the name and token to ensure it's distinct.
    # This is important for Home Assistant to track the entity correctly.
    unique_id = f"xgimi_{name}_{token}"  # Prefixed for clarity
    _LOGGER.debug("Derived unique ID for XGIMI remote: %s", unique_id)

    # Use imported constants for ports
    xgimi_api = XgimiApi(
        ip=host,
        command_port=XGIMI_COMMAND_PORT,
        advance_port=XGIMI_ADVANCE_PORT,
        alive_port=XGIMI_ALIVE_PORT,
        manufacturer_data=token,
    )

    _LOGGER.info("Creating XgimiRemote entity: %s (Host: %s)", name, host)
    async_add_entities([XgimiRemote(xgimi_api, name, unique_id)])
    _LOGGER.debug("XgimiRemote entity for %s added.", name)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,  # Configuration entry from UI flow
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up the XGIMI projector platform from a config entry (UI flow).

    This function is invoked when a XGIMI projector is configured via the UI.
    It retrieves the configuration, initializes the API, and creates the remote entity.

    Args:
        hass: The Home Assistant instance.
        config_entry: The configuration entry containing the device details.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    _LOGGER.info(
        "Setting up XGIMI entry for %s (ID: %s)",
        config_entry.title,
        config_entry.entry_id,
    )
    # Retrieve configuration stored during the config flow
    config = hass.data[DOMAIN][config_entry.entry_id]
    host = config[CONF_HOST]
    name = config[CONF_NAME]
    # CONF_TOKEN is used as manufacturer_data for BLE power-on
    token = config[CONF_TOKEN]

    # The unique_id is typically provided by the config_entry itself,
    # ensuring consistency across Home Assistant restarts.
    unique_id = config_entry.unique_id
    assert unique_id is not None  # Should always be present for config entries
    _LOGGER.debug("Using unique ID from config entry: %s", unique_id)

    # Use imported constants for ports
    xgimi_api = XgimiApi(
        ip=host,
        command_port=XGIMI_COMMAND_PORT,
        advance_port=XGIMI_ADVANCE_PORT,
        alive_port=XGIMI_ALIVE_PORT,
        manufacturer_data=token,
    )

    _LOGGER.info(
        "Creating XgimiRemote entity: %s (Host: %s, Unique ID: %s)",
        name,
        host,
        unique_id,
    )
    async_add_entities([XgimiRemote(xgimi_api, name, unique_id)])
    _LOGGER.debug("XgimiRemote entity for %s (Unique ID: %s) added.", name, unique_id)


class XgimiRemote(RemoteEntity):
    """
    Represents a XGIMI Projector as a RemoteEntity in Home Assistant.

    This class handles the state and control of the projector, interfacing
    with the XgimiApi.
    """

    def __init__(self, xgimi_api: XgimiApi, name: str, unique_id: str) -> None:
        """
        Initialize the XgimiRemote entity.

        Args:
            xgimi_api: An instance of XgimiApi for communication with the projector.
            name: The display name of the remote entity.
            unique_id: The unique identifier for this entity.
        """
        _LOGGER.info("Initializing XgimiRemote: %s (Unique ID: %s)", name, unique_id)
        self.xgimi_api = xgimi_api
        self._name = name
        self._icon = "mdi:projector"  # Default icon for projector
        self._unique_id = unique_id
        _LOGGER.debug("XgimiRemote %s initialized with API.", name)

    async def async_update(self) -> None:
        """
        Retrieve the latest state of the projector.

        This method is called periodically by Home Assistant to update the entity's state.
        """
        _LOGGER.debug("Fetching update for XgimiRemote: %s", self._name)
        try:
            await self.xgimi_api.async_fetch_data()
            _LOGGER.debug(
                "Update fetched for %s. Is on: %s", self._name, self.xgimi_api.is_on
            )
        except Exception as e:
            _LOGGER.error("Error during async_update for %s: %s", self._name, e)

    @property
    def is_on(self) -> bool:
        """Return true if the projector is considered on."""
        # Uses the public property of XgimiApi now
        return self.xgimi_api.is_on

    @property
    def name(self) -> str:
        """Return the display name of the remote."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the icon to use for the remote in the UI."""
        return self._icon

    @property
    def unique_id(self) -> str:
        """Return the unique ID of this remote entity."""
        return self._unique_id

    async def async_turn_on(self, **kwargs) -> None:
        """
        Turn the XGIMI Projector On.

        This method sends the "poweron" command via the XgimiApi.
        """
        _LOGGER.info("Turning on XGIMI Projector: %s", self._name)
        try:
            await self.xgimi_api.async_send_command("poweron")
            _LOGGER.debug("Power on command sent to %s.", self._name)
        except Exception as e:
            _LOGGER.error("Error turning on %s: %s", self._name, e)

    async def async_turn_off(self, **kwargs) -> None:
        """
        Turn the XGIMI Projector Off.

        This method sends the "poweroff" command via the XgimiApi.
        """
        _LOGGER.info("Turning off XGIMI Projector: %s", self._name)
        try:
            await self.xgimi_api.async_send_command("poweroff")
            _LOGGER.debug("Power off command sent to %s.", self._name)
        except Exception as e:
            _LOGGER.error("Error turning off %s: %s", self._name, e)

    async def async_send_command(self, command: Iterable[str], **kwargs) -> None:
        """
        Send a sequence of commands to the XGIMI Projector.

        Args:
            command: An iterable of command strings to be sent.
            **kwargs: Additional arguments (not used by this implementation).
        """
        _LOGGER.info("Sending commands to %s: %s", self._name, command)
        try:
            for single_command in command:
                _LOGGER.debug(
                    "Sending single command '%s' to %s", single_command, self._name
                )
                await self.xgimi_api.async_send_command(single_command)
            _LOGGER.debug("All commands (%s) sent to %s.", command, self._name)
        except Exception as e:
            _LOGGER.error(
                "Error sending command(s) %s to %s: %s", command, self._name, e
            )

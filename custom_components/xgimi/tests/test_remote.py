import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN

from custom_components.xgimi.const import (
    DOMAIN,
    XGIMI_COMMAND_PORT,
    XGIMI_ADVANCE_PORT,
    XGIMI_ALIVE_PORT,
)
from custom_components.xgimi.remote import (
    async_setup_platform,
    async_setup_entry,
    XgimiRemote,
)
from custom_components.xgimi.pyxgimi import XgimiApi

# This ensures pytest-asyncio is used
pytest_plugins = "pytest_asyncio"

MOCK_HOST = "1.2.3.4"
MOCK_NAME = "Test Projector"
MOCK_TOKEN = "test_token_manufacturer_data"  # Also used as manufacturer_data
MOCK_UNIQUE_ID_PLATFORM = f"xgimi_{MOCK_NAME}_{MOCK_TOKEN}"
MOCK_UNIQUE_ID_ENTRY = (
    f"{MOCK_NAME}-{MOCK_TOKEN}"  # As per current config_flow logic for unique_id
)


@pytest.fixture
def mock_xgimi_api():
    """Fixture for a mock XgimiApi instance."""
    api = AsyncMock(spec=XgimiApi)
    api.ip = MOCK_HOST
    api.command_port = XGIMI_COMMAND_PORT
    api.advance_port = XGIMI_ADVANCE_PORT
    api.alive_port = XGIMI_ALIVE_PORT
    api.manufacturer_data = MOCK_TOKEN
    # Configure is_on as a property that can be set
    type(api).is_on = MagicMock(
        return_value=True
    )  # Default to True, can be changed in tests
    return api


@pytest.fixture
def mock_config_entry():
    """Fixture for a mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "mock_entry_id"
    entry.unique_id = MOCK_UNIQUE_ID_ENTRY
    entry.title = MOCK_NAME
    return entry


@pytest.fixture
def hass():
    """Fixture for a HomeAssistant instance."""
    # Basic mock, can be expanded if more HASS features are needed
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def remote_entity(mock_xgimi_api: AsyncMock):
    """Fixture to initialize XgimiRemote with a mock API."""
    return XgimiRemote(
        xgimi_api=mock_xgimi_api, name=MOCK_NAME, unique_id=MOCK_UNIQUE_ID_ENTRY
    )


# Tests for async_setup_platform (Legacy)
@patch("custom_components.xgimi.remote.XgimiApi")
async def test_async_setup_platform(mock_xgimi_api_cls: MagicMock, hass: HomeAssistant):
    """Test the legacy async_setup_platform function."""
    mock_add_entities_callback = MagicMock()
    mock_api_instance = AsyncMock(spec=XgimiApi)
    mock_xgimi_api_cls.return_value = mock_api_instance

    config = {
        CONF_HOST: MOCK_HOST,
        CONF_NAME: MOCK_NAME,
        CONF_TOKEN: MOCK_TOKEN,  # This is used as manufacturer_data
    }

    await async_setup_platform(hass, config, mock_add_entities_callback, {})

    mock_xgimi_api_cls.assert_called_once_with(
        ip=MOCK_HOST,
        command_port=XGIMI_COMMAND_PORT,
        advance_port=XGIMI_ADVANCE_PORT,
        alive_port=XGIMI_ALIVE_PORT,
        manufacturer_data=MOCK_TOKEN,
    )

    assert mock_add_entities_callback.call_count == 1
    added_entities = mock_add_entities_callback.call_args[0][0]
    assert len(added_entities) == 1
    entity = added_entities[0]
    assert isinstance(entity, XgimiRemote)
    assert entity.name == MOCK_NAME
    assert entity.unique_id == MOCK_UNIQUE_ID_PLATFORM  # Legacy unique_id format


# Tests for async_setup_entry
@patch("custom_components.xgimi.remote.XgimiApi")
async def test_async_setup_entry(
    mock_xgimi_api_cls: MagicMock, hass: HomeAssistant, mock_config_entry: ConfigEntry
):
    """Test the async_setup_entry function."""
    mock_add_entities_callback = MagicMock()
    mock_api_instance = AsyncMock(spec=XgimiApi)
    mock_xgimi_api_cls.return_value = mock_api_instance

    # Setup hass.data for the config entry
    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                CONF_HOST: MOCK_HOST,
                CONF_NAME: MOCK_NAME,
                CONF_TOKEN: MOCK_TOKEN,  # Used as manufacturer_data
            }
        }
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities_callback)

    mock_xgimi_api_cls.assert_called_once_with(
        ip=MOCK_HOST,
        command_port=XGIMI_COMMAND_PORT,
        advance_port=XGIMI_ADVANCE_PORT,
        alive_port=XGIMI_ALIVE_PORT,
        manufacturer_data=MOCK_TOKEN,
    )

    assert mock_add_entities_callback.call_count == 1
    added_entities = mock_add_entities_callback.call_args[0][0]
    assert len(added_entities) == 1
    entity = added_entities[0]
    assert isinstance(entity, XgimiRemote)
    assert entity.name == MOCK_NAME
    assert entity.unique_id == MOCK_UNIQUE_ID_ENTRY


# Tests for XgimiRemote Entity
def test_remote_properties(remote_entity: XgimiRemote):
    """Test the basic properties of the XgimiRemote entity."""
    assert remote_entity.name == MOCK_NAME
    assert remote_entity.icon == "mdi:projector"
    assert remote_entity.unique_id == MOCK_UNIQUE_ID_ENTRY


def test_remote_is_on(remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock):
    """Test the is_on property of the XgimiRemote entity."""
    # Test when API reports True
    type(mock_xgimi_api).is_on = True  # Configure the MagicMock property
    assert remote_entity.is_on is True

    # Test when API reports False
    type(mock_xgimi_api).is_on = False  # Configure the MagicMock property
    assert remote_entity.is_on is False


async def test_remote_async_update(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock
):
    """Test the async_update method."""
    await remote_entity.async_update()
    mock_xgimi_api.async_fetch_data.assert_called_once()


async def test_remote_async_turn_on(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock
):
    """Test the async_turn_on method."""
    await remote_entity.async_turn_on()
    mock_xgimi_api.async_send_command.assert_called_once_with("poweron")


async def test_remote_async_turn_off(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock
):
    """Test the async_turn_off method."""
    await remote_entity.async_turn_off()
    mock_xgimi_api.async_send_command.assert_called_once_with("poweroff")


async def test_remote_async_send_command(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock
):
    """Test the async_send_command method."""
    commands = ["menu", "home", "volumedown"]
    await remote_entity.async_send_command(commands)

    expected_calls = [call(command) for command in commands]
    mock_xgimi_api.async_send_command.assert_has_calls(expected_calls)
    assert mock_xgimi_api.async_send_command.call_count == len(commands)


# Additional test for async_setup_platform with missing config
@patch("custom_components.xgimi.remote.XgimiApi")
async def test_async_setup_platform_missing_config(
    mock_xgimi_api_cls: MagicMock, hass: HomeAssistant, caplog
):
    """Test async_setup_platform with missing configuration keys."""
    mock_add_entities_callback = MagicMock()

    # Test with missing host
    config_missing_host = {CONF_NAME: MOCK_NAME, CONF_TOKEN: MOCK_TOKEN}
    await async_setup_platform(
        hass, config_missing_host, mock_add_entities_callback, {}
    )
    assert (
        "Missing required configuration for XGIMI (host, name, or token)" in caplog.text
    )
    mock_xgimi_api_cls.assert_not_called()
    mock_add_entities_callback.assert_not_called()
    caplog.clear()

    # Test with missing name
    config_missing_name = {CONF_HOST: MOCK_HOST, CONF_TOKEN: MOCK_TOKEN}
    await async_setup_platform(
        hass, config_missing_name, mock_add_entities_callback, {}
    )
    assert (
        "Missing required configuration for XGIMI (host, name, or token)" in caplog.text
    )
    mock_xgimi_api_cls.assert_not_called()
    mock_add_entities_callback.assert_not_called()
    caplog.clear()

    # Test with missing token
    config_missing_token = {CONF_HOST: MOCK_HOST, CONF_NAME: MOCK_NAME}
    await async_setup_platform(
        hass, config_missing_token, mock_add_entities_callback, {}
    )
    assert (
        "Missing required configuration for XGIMI (host, name, or token)" in caplog.text
    )
    mock_xgimi_api_cls.assert_not_called()
    mock_add_entities_callback.assert_not_called()


# Test for unique_id assertion in async_setup_entry
@patch("custom_components.xgimi.remote.XgimiApi")
async def test_async_setup_entry_no_unique_id(
    mock_xgimi_api_cls: MagicMock,
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog,
):
    """Test async_setup_entry when config_entry has no unique_id (should assert)."""
    mock_add_entities_callback = MagicMock()
    mock_config_entry.unique_id = None  # Simulate missing unique_id

    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                CONF_HOST: MOCK_HOST,
                CONF_NAME: MOCK_NAME,
                CONF_TOKEN: MOCK_TOKEN,
            }
        }
    }

    with pytest.raises(AssertionError):  # Expecting an AssertionError
        await async_setup_entry(hass, mock_config_entry, mock_add_entities_callback)

    mock_xgimi_api_cls.assert_not_called()  # Should not proceed to API init
    mock_add_entities_callback.assert_not_called()


# Test error handling in XgimiRemote methods (example for async_update)
async def test_remote_async_update_exception(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock, caplog
):
    """Test exception handling in async_update."""
    mock_xgimi_api.async_fetch_data.side_effect = Exception("API Fetch Error")
    await remote_entity.async_update()
    assert "Error during async_update" in caplog.text
    assert "API Fetch Error" in caplog.text


async def test_remote_async_turn_on_exception(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock, caplog
):
    """Test exception handling in async_turn_on."""
    mock_xgimi_api.async_send_command.side_effect = Exception("API Turn On Error")
    await remote_entity.async_turn_on()
    assert f"Error turning on {remote_entity.name}" in caplog.text
    assert "API Turn On Error" in caplog.text


async def test_remote_async_turn_off_exception(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock, caplog
):
    """Test exception handling in async_turn_off."""
    mock_xgimi_api.async_send_command.side_effect = Exception("API Turn Off Error")
    await remote_entity.async_turn_off()
    assert f"Error turning off {remote_entity.name}" in caplog.text
    assert "API Turn Off Error" in caplog.text


async def test_remote_async_send_command_exception(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock, caplog
):
    """Test exception handling in async_send_command."""
    commands = ["menu"]
    mock_xgimi_api.async_send_command.side_effect = Exception("API Send Error")
    await remote_entity.async_send_command(commands)
    assert f"Error sending command(s) {commands} to {remote_entity.name}" in caplog.text
    assert "API Send Error" in caplog.text


# Test XgimiRemote initialization logging
def test_remote_init_logging(mock_xgimi_api: AsyncMock, caplog):
    """Test logging during XgimiRemote initialization."""
    # caplog.set_level(logging.INFO) # Ensure INFO logs are captured if not default
    # Remote variable was assigned but not used. Instantiation is enough for logging.
    XgimiRemote(mock_xgimi_api, "LogTest", "log_test_id_123")
    assert (
        "Initializing XgimiRemote: LogTest (Unique ID: log_test_id_123)" in caplog.text
    )
    assert "XgimiRemote LogTest initialized with API" in caplog.text


# Test async_setup_platform logging
@patch("custom_components.xgimi.remote.XgimiApi")
async def test_async_setup_platform_logging(
    mock_xgimi_api_cls: MagicMock, hass: HomeAssistant, caplog
):
    """Test logging in async_setup_platform."""
    mock_add_entities_callback = MagicMock()
    config = {CONF_HOST: MOCK_HOST, CONF_NAME: "PlatformLogger", CONF_TOKEN: "tokenlog"}

    await async_setup_platform(hass, config, mock_add_entities_callback, {})

    assert "Setting up XGIMI platform from YAML configuration." in caplog.text
    assert (
        "Derived unique ID for XGIMI remote: xgimi_PlatformLogger_tokenlog"
        in caplog.text
    )
    assert "Creating XgimiRemote entity: PlatformLogger (Host: 1.2.3.4)" in caplog.text
    assert "XgimiRemote entity for PlatformLogger added." in caplog.text


# Test async_setup_entry logging
@patch("custom_components.xgimi.remote.XgimiApi")
async def test_async_setup_entry_logging(
    mock_xgimi_api_cls: MagicMock,
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog,
):
    """Test logging in async_setup_entry."""
    mock_add_entities_callback = MagicMock()
    mock_config_entry.title = "EntryLogger"
    mock_config_entry.unique_id = "entry_logger_uid"

    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                CONF_HOST: MOCK_HOST,
                CONF_NAME: "EntryLogger",
                CONF_TOKEN: MOCK_TOKEN,
            }
        }
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities_callback)

    assert (
        f"Setting up XGIMI entry for EntryLogger (ID: {mock_config_entry.entry_id})"
        in caplog.text
    )
    assert "Using unique ID from config entry: entry_logger_uid" in caplog.text
    assert (
        "Creating XgimiRemote entity: EntryLogger (Host: 1.2.3.4, Unique ID: entry_logger_uid)"
        in caplog.text
    )
    assert (
        "XgimiRemote entity for EntryLogger (Unique ID: entry_logger_uid) added."
        in caplog.text
    )


# Test XgimiRemote method logging
async def test_remote_method_logging(
    remote_entity: XgimiRemote, mock_xgimi_api: AsyncMock, caplog
):
    """Test logging within XgimiRemote methods."""
    # async_update
    await remote_entity.async_update()
    assert f"Fetching update for XgimiRemote: {MOCK_NAME}" in caplog.text
    assert (
        f"Update fetched for {MOCK_NAME}. Is on: True" in caplog.text
    )  # Assumes is_on is True by default from fixture
    caplog.clear()

    # async_turn_on
    await remote_entity.async_turn_on()
    assert f"Turning on XGIMI Projector: {MOCK_NAME}" in caplog.text
    assert f"Power on command sent to {MOCK_NAME}." in caplog.text
    caplog.clear()

    # async_turn_off
    await remote_entity.async_turn_off()
    assert f"Turning off XGIMI Projector: {MOCK_NAME}" in caplog.text
    assert f"Power off command sent to {MOCK_NAME}." in caplog.text
    caplog.clear()

    # async_send_command
    commands = ["test_cmd"]
    await remote_entity.async_send_command(commands)
    assert f"Sending commands to {MOCK_NAME}: {commands}" in caplog.text
    assert f"Sending single command 'test_cmd' to {MOCK_NAME}" in caplog.text
    assert f"All commands ({commands}) sent to {MOCK_NAME}." in caplog.text


# Note: The `is_on` property on `mock_xgimi_api` is configured using `type(api).is_on = MagicMock(...)`.
# This is a way to mock properties on a mock object that itself is an AsyncMock.
# If `is_on` were an async method, it would be part of `AsyncMock` directly.
# The use of `caplog` fixture is for testing `_LOGGER` outputs.
# It's assumed `pytest-asyncio` is correctly handling the event loop for `async def` tests.
# `pytest-homeassistant-custom-component` is not strictly needed if HASS fixtures are basic mocks,
# but would be essential for deeper HASS integration testing.
# The unique_id for platform setup is `xgimi_{name}_{token}` as per current code.
# The unique_id for entry setup is taken from `config_entry.unique_id` which is `{name}-{token}` from config_flow.
# This difference is reflected in the MOCK_UNIQUE_ID constants.

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, call
from time import time

from custom_components.xgimi.pyxgimi import XgimiApi
from custom_components.xgimi.const import (
    XGIMI_COMMAND_PORT,
    XGIMI_ADVANCE_PORT,
    XGIMI_ALIVE_PORT,
)

# This ensures pytest-asyncio is used
pytest_plugins = "pytest_asyncio"

# Mock data
MOCK_IP = "192.168.1.100"
MOCK_MANUFACTURER_DATA = "aabbccddeeff"
MOCK_COMMAND_PORT = XGIMI_COMMAND_PORT
MOCK_ADVANCE_PORT = XGIMI_ADVANCE_PORT
MOCK_ALIVE_PORT = XGIMI_ALIVE_PORT


@pytest.fixture
def api():
    """Fixture to create an XgimiApi instance for tests."""
    return XgimiApi(
        ip=MOCK_IP,
        command_port=MOCK_COMMAND_PORT,
        advance_port=MOCK_ADVANCE_PORT,
        alive_port=MOCK_ALIVE_PORT,
        manufacturer_data=MOCK_MANUFACTURER_DATA,
    )


# Test for XgimiApi.__init__
async def test_xgimi_api_initialization(api: XgimiApi):
    """Test the initialization of XgimiApi."""
    assert api.ip == MOCK_IP
    assert api.command_port == MOCK_COMMAND_PORT
    assert api.advance_port == MOCK_ADVANCE_PORT
    assert api.alive_port == MOCK_ALIVE_PORT
    assert api.manufacturer_data == MOCK_MANUFACTURER_DATA
    assert not api._is_on  # Should be False initially
    assert api.last_on is not None
    assert api.last_off is not None
    # Check command dict and advance command format are present
    assert "ok" in api._command_dict
    assert "command_holder" in api._advance_command


# Tests for XgimiApi.async_check_alive
@patch("asyncio.open_connection", new_callable=AsyncMock)
async def test_async_check_alive_success(
    mock_open_connection: AsyncMock, api: XgimiApi
):
    """Test async_check_alive successfully connects."""
    mock_reader, mock_writer = AsyncMock(), AsyncMock()
    mock_open_connection.return_value = (mock_reader, mock_writer)

    result = await api.async_check_alive()

    assert result is True
    mock_open_connection.assert_called_once_with(MOCK_IP, MOCK_ALIVE_PORT)
    mock_writer.close.assert_called_once()
    await mock_writer.wait_closed()  # Ensure wait_closed is awaited


@patch("asyncio.open_connection", new_callable=AsyncMock)
async def test_async_check_alive_failure_refused(
    mock_open_connection: AsyncMock, api: XgimiApi
):
    """Test async_check_alive when connection is refused."""
    mock_open_connection.side_effect = ConnectionRefusedError

    result = await api.async_check_alive()

    assert result is False
    mock_open_connection.assert_called_once_with(MOCK_IP, MOCK_ALIVE_PORT)


@patch("asyncio.open_connection", new_callable=AsyncMock)
async def test_async_check_alive_failure_timeout(
    mock_open_connection: AsyncMock, api: XgimiApi
):
    """Test async_check_alive when connection times out."""
    mock_open_connection.side_effect = asyncio.TimeoutError

    result = await api.async_check_alive()

    assert result is False
    mock_open_connection.assert_called_once_with(MOCK_IP, MOCK_ALIVE_PORT)


@patch("asyncio.open_connection", new_callable=AsyncMock)
async def test_async_check_alive_failure_exception(
    mock_open_connection: AsyncMock, api: XgimiApi
):
    """Test async_check_alive with a generic OSError."""
    mock_open_connection.side_effect = OSError("Test OS Error")

    result = await api.async_check_alive()

    assert result is False
    mock_open_connection.assert_called_once_with(MOCK_IP, MOCK_ALIVE_PORT)


# Tests for XgimiApi.async_send_command (Standard Commands)
@patch("custom_components.xgimi.pyxgimi.asyncudp.create_socket", new_callable=AsyncMock)
async def test_async_send_command_standard(
    mock_create_socket: AsyncMock, api: XgimiApi
):
    """Test sending various standard commands."""
    mock_socket = AsyncMock()
    mock_create_socket.return_value = mock_socket

    standard_commands = ["ok", "back", "volumeup"]
    for command in standard_commands:
        mock_create_socket.reset_mock()  # Reset for each command
        mock_socket.reset_mock()

        await api.async_send_command(command)

        expected_payload = api._command_dict[command].encode("utf-8")
        mock_create_socket.assert_called_once_with(
            remote_addr=(MOCK_IP, MOCK_COMMAND_PORT)
        )
        mock_socket.sendto.assert_called_once_with(expected_payload)
        mock_socket.close.assert_called_once()

    # Test "poweroff" specifically
    mock_create_socket.reset_mock()
    mock_socket.reset_mock()
    api._is_on = True  # Set to on to check if it's turned off
    start_time = time()
    await asyncio.sleep(0.01)  # ensure time changes

    await api.async_send_command("poweroff")

    expected_payload = api._command_dict["poweroff"].encode("utf-8")
    mock_create_socket.assert_called_once_with(remote_addr=(MOCK_IP, MOCK_COMMAND_PORT))
    mock_socket.sendto.assert_called_once_with(expected_payload)
    mock_socket.close.assert_called_once()
    assert api._is_on is False
    assert api.last_off > start_time


# Tests for XgimiApi.async_send_command (Advanced Commands)
@patch("custom_components.xgimi.pyxgimi.asyncudp.create_socket", new_callable=AsyncMock)
async def test_async_send_command_advanced(
    mock_create_socket: AsyncMock, api: XgimiApi
):
    """Test sending an advanced command."""
    mock_socket = AsyncMock()
    mock_create_socket.return_value = mock_socket
    advanced_command = "test_advanced_cmd"

    await api.async_send_command(advanced_command)

    expected_payload = api._advance_command.replace(
        "command_holder", advanced_command
    ).encode("utf-8")
    mock_create_socket.assert_called_once_with(remote_addr=(MOCK_IP, MOCK_ADVANCE_PORT))
    mock_socket.sendto.assert_called_once_with(expected_payload)
    mock_socket.close.assert_called_once()


# Tests for XgimiApi.async_send_command (Power On Command)
@patch.object(XgimiApi, "async_robust_ble_power_on", new_callable=AsyncMock)
async def test_async_send_command_poweron(
    mock_robust_ble_power_on: AsyncMock, api: XgimiApi
):
    """Test sending the 'poweron' command."""
    api._is_on = False  # Set to off to check if it's turned on
    start_time = time()
    await asyncio.sleep(0.01)  # ensure time changes

    await api.async_send_command("poweron")

    mock_robust_ble_power_on.assert_called_once_with(MOCK_MANUFACTURER_DATA)
    assert api._is_on is True
    assert api.last_on > start_time


# Tests for XgimiApi.async_ble_power_on and XgimiApi.async_robust_ble_power_on
@patch("custom_components.xgimi.pyxgimi.Advertisement")
@patch("custom_components.xgimi.pyxgimi.get_message_bus", new_callable=AsyncMock)
async def test_async_ble_power_on(
    mock_get_message_bus: AsyncMock, mock_advertisement_cls: MagicMock, api: XgimiApi
):
    """Test the async_ble_power_on method."""
    mock_bus = AsyncMock()
    mock_get_message_bus.return_value = mock_bus
    mock_advert_instance = AsyncMock()  # Mock the instance of Advertisement
    mock_advertisement_cls.return_value = mock_advert_instance

    test_mfg_data = "fedcba987654"
    await api.async_ble_power_on(test_mfg_data)

    mock_get_message_bus.assert_called_once()
    mock_advertisement_cls.assert_called_once_with(
        localName="Bluetooth 4.0 RC",
        serviceUUIDs=["1812"],
        manufacturerData={0x0046: bytes.fromhex(test_mfg_data)},
        timeout=1,
        duration=1000,
        appearance=961,
    )
    mock_advert_instance.register.assert_called_once_with(mock_bus)


@patch.object(XgimiApi, "async_ble_power_on", new_callable=AsyncMock)
async def test_async_robust_ble_power_on_success(
    mock_async_ble_power_on: AsyncMock, api: XgimiApi
):
    """Test async_robust_ble_power_on successfully calls async_ble_power_on."""
    test_mfg_data = "123456abcdef"
    await api.async_robust_ble_power_on(test_mfg_data)

    # Should succeed on the first try
    mock_async_ble_power_on.assert_called_once_with(test_mfg_data, 0x0046, "1812")


@patch.object(XgimiApi, "async_ble_power_on", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)  # Mock asyncio.sleep
async def test_async_robust_ble_power_on_retries_and_fails(
    mock_sleep: AsyncMock, mock_async_ble_power_on: AsyncMock, api: XgimiApi
):
    """Test async_robust_ble_power_on retries 10 times on failure."""
    mock_async_ble_power_on.side_effect = Exception("BLE Power On Failed")
    test_mfg_data = "abcdef123456"

    # We expect this to log errors, but we're checking call counts here
    await api.async_robust_ble_power_on(test_mfg_data)

    assert mock_async_ble_power_on.call_count == 10
    # Check it's called with the correct args each time
    mock_async_ble_power_on.assert_has_calls([call(test_mfg_data, 0x0046, "1812")] * 10)
    assert mock_sleep.call_count == 10  # Sleeps 10 times, once after each failed attempt


# Tests for XgimiApi.async_fetch_data
@patch("custom_components.xgimi.pyxgimi.time")  # Patch time from where it's used
@patch.object(XgimiApi, "async_check_alive", new_callable=AsyncMock)
async def test_async_fetch_data_recent_on(
    mock_async_check_alive: AsyncMock, mock_pyxgimi_time: MagicMock, api: XgimiApi
):
    """Test async_fetch_data when recently turned on."""
    current_time_val = time()  # Get a real timestamp
    mock_pyxgimi_time.return_value = current_time_val  # Mock time() in pyxgimi.py

    api.last_on = current_time_val - 10  # 10 seconds ago
    api.last_off = current_time_val - 60  # 60 seconds ago

    api._is_on = False  # Start with off state
    await api.async_fetch_data()

    assert api._is_on is True
    mock_async_check_alive.assert_not_called()


@patch("custom_components.xgimi.pyxgimi.time")  # Patch time from where it's used
@patch.object(XgimiApi, "async_check_alive", new_callable=AsyncMock)
async def test_async_fetch_data_recent_off(
    mock_async_check_alive: AsyncMock, mock_pyxgimi_time: MagicMock, api: XgimiApi
):
    """Test async_fetch_data when recently turned off."""
    current_time_val = time()
    mock_pyxgimi_time.return_value = current_time_val

    api.last_on = current_time_val - 60  # 60 seconds ago
    api.last_off = current_time_val - 10  # 10 seconds ago

    api._is_on = True  # Start with on state
    await api.async_fetch_data()

    assert api._is_on is False
    mock_async_check_alive.assert_not_called()


@patch("custom_components.xgimi.pyxgimi.time")  # Patch time from where it's used
@patch.object(XgimiApi, "async_check_alive", new_callable=AsyncMock)
async def test_async_fetch_data_check_alive_true(
    mock_async_check_alive: AsyncMock, mock_pyxgimi_time: MagicMock, api: XgimiApi
):
    """Test async_fetch_data when active check is needed and projector is alive."""
    current_time_val = time()
    mock_pyxgimi_time.return_value = current_time_val

    api.last_on = current_time_val - 60  # More than 30s ago
    api.last_off = current_time_val - 60  # More than 30s ago
    mock_async_check_alive.return_value = True

    api._is_on = False  # Start with off state
    await api.async_fetch_data()

    assert api._is_on is True
    mock_async_check_alive.assert_called_once()


@patch("custom_components.xgimi.pyxgimi.time")  # Patch time from where it's used
@patch.object(XgimiApi, "async_check_alive", new_callable=AsyncMock)
async def test_async_fetch_data_check_alive_false(
    mock_async_check_alive: AsyncMock, mock_pyxgimi_time: MagicMock, api: XgimiApi
):
    """Test async_fetch_data when active check is needed and projector is not alive."""
    current_time_val = time()
    mock_pyxgimi_time.return_value = current_time_val

    api.last_on = current_time_val - 60  # More than 30s ago
    api.last_off = current_time_val - 60  # More than 30s ago
    mock_async_check_alive.return_value = False

    api._is_on = True  # Start with on state
    await api.async_fetch_data()

    assert api._is_on is False
    mock_async_check_alive.assert_called_once()

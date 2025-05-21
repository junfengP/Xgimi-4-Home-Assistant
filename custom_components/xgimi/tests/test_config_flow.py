import pytest
from unittest.mock import patch, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xgimi.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN

# This ensures pytest-asyncio is used
pytest_plugins = "pytest_asyncio"

MOCK_HOST = "1.2.3.4"
MOCK_VALID_HOST = "4.3.2.1"  # Different from MOCK_HOST for distinction
MOCK_NAME = "Test Xgimi Projector"
MOCK_TOKEN = "my_secret_token"
MOCK_UNIQUE_ID = f"{MOCK_NAME}-{MOCK_TOKEN}"


@pytest.fixture
def hass():
    """Fixture for a HomeAssistant instance."""
    # Basic mock, can be expanded if more HASS features are needed
    hass_obj = MagicMock(spec=HomeAssistant)
    hass_obj.config_entries = MagicMock()  # Mock config_entries manager
    # Mock async_entries to return a list of existing entries
    hass_obj.config_entries.async_entries = MagicMock(return_value=[])
    return hass_obj


# --- Test User Step ---


async def test_config_flow_user_step_show_form_initial(hass: HomeAssistant):
    """Test showing the form for the user step, initial call."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None  # Should be None or {} for initial form


@patch("custom_components.xgimi.config_flow.is_host_valid", return_value=True)
async def test_config_flow_user_step_success(
    mock_is_host_valid: MagicMock, hass: HomeAssistant
):
    """Test user step success: valid host, new entry."""
    # Initialize the flow
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    flow_id = result_init["flow_id"]

    user_input = {
        CONF_NAME: MOCK_NAME,
        CONF_HOST: MOCK_VALID_HOST,  # Use a host that is_host_valid will confirm
        CONF_TOKEN: MOCK_TOKEN,
    }

    result_configure = await hass.config_entries.flow.async_configure(
        flow_id, user_input
    )

    mock_is_host_valid.assert_called_once_with(MOCK_VALID_HOST)
    assert result_configure["type"] == FlowResultType.CREATE_ENTRY
    assert result_configure["title"] == MOCK_NAME
    assert result_configure["data"] == user_input
    assert "result" in result_configure  # Config entry object should be in result key
    created_entry = result_configure["result"]
    assert created_entry.unique_id == MOCK_UNIQUE_ID


@patch("custom_components.xgimi.config_flow.is_host_valid", return_value=False)
async def test_config_flow_user_step_invalid_host(
    mock_is_host_valid: MagicMock, hass: HomeAssistant
):
    """Test user step with an invalid host."""
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    flow_id = result_init["flow_id"]

    user_input_invalid_host = {
        CONF_NAME: MOCK_NAME,
        CONF_HOST: "invalid-hostname-or-ip",
        CONF_TOKEN: MOCK_TOKEN,
    }

    result_configure = await hass.config_entries.flow.async_configure(
        flow_id, user_input_invalid_host
    )

    mock_is_host_valid.assert_called_once_with("invalid-hostname-or-ip")
    assert result_configure["type"] == FlowResultType.FORM
    assert result_configure["step_id"] == "user"
    assert result_configure["errors"] == {CONF_HOST: "invalid_host"}


async def test_config_flow_user_step_already_configured(hass: HomeAssistant):
    """Test user step when the projector (unique ID) is already configured."""
    # Simulate an already configured entry by setting its unique_id
    # The actual ConfigEntry object and its state are not deeply checked by _abort_if_unique_id_configured,
    # just the presence of its unique_id.

    # To properly mock this, we need to make hass.config_entries.async_entries return an entry
    # OR, if XgimiConfigFlow uses self._async_current_entries() which uses hass.config_entries.async_entries(DOMAIN)
    # we can mock that. For XGIMI, it uses self.async_set_unique_id and _abort_if_unique_id_configured.
    # The _abort_if_unique_id_configured checks against self._config_entry.config_entries.async_entries(DOMAIN)
    # if self._unique_id is already present.

    # Let's first successfully configure one
    with patch("custom_components.xgimi.config_flow.is_host_valid", return_value=True):
        result_init1 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        flow_id1 = result_init1["flow_id"]
        user_input1 = {
            CONF_NAME: MOCK_NAME,
            CONF_HOST: MOCK_VALID_HOST,
            CONF_TOKEN: MOCK_TOKEN,
        }
        # This will register the unique_id MOCK_UNIQUE_ID
        await hass.config_entries.flow.async_configure(flow_id1, user_input1)

    # Now, attempt to configure another one with the same details (leading to same unique_id)
    result_init2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    flow_id2 = result_init2["flow_id"]
    user_input2 = {  # Same input, so same unique_id
        CONF_NAME: MOCK_NAME,
        CONF_HOST: "another.valid.host.com",  # Host can be different
        CONF_TOKEN: MOCK_TOKEN,  # Name and Token define unique_id
    }

    # This call should lead to _abort_if_unique_id_configured
    result_configure2 = await hass.config_entries.flow.async_configure(
        flow_id2, user_input2
    )

    assert result_configure2["type"] == FlowResultType.ABORT
    assert result_configure2["reason"] == "already_configured"


# --- Test is_host_valid ---
# The actual is_host_valid function is simple, but good to have a placeholder
# or test its behavior if it becomes complex. For now, it's mocked.
# If you want to test the real `is_host_valid` (which is not part of this subtask's direct request for config_flow.py tests):
# from custom_components.xgimi.config_flow import is_host_valid
# def test_is_host_valid_function():
#     assert is_host_valid("192.168.1.1") is True
#     assert is_host_valid("valid-hostname.com") is True
#     assert is_host_valid("invalid host name") is False # Contains space
#     assert is_host_valid("") is False
#     assert is_host_valid(None) is False


# --- Test Options Flow (Placeholder if not implemented) ---
# If an options flow were implemented, tests would go here. Example:
# async def test_options_flow(hass: HomeAssistant):
#     """Test the options flow if it existed."""
#     # Setup a config entry
#     config_entry = MagicMock(spec=ConfigEntry)
#     config_entry.entry_id = "test_entry_id_options"
#     config_entry.data = {CONF_HOST: MOCK_HOST, CONF_NAME: MOCK_NAME, CONF_TOKEN: MOCK_TOKEN}
#     config_entry.options = {} # Initial options
#
#     # Initialize options flow
#     result = await hass.config_entries.options.async_init(config_entry.entry_id)
#     assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
#     assert result["step_id"] == "init" # Or whatever the first step is
#
#     # Simulate user input for options
#     options_input = {"some_option": "new_value"}
#     result_save = await hass.config_entries.options.async_configure(
#         result["flow_id"], user_input=options_input
#     )
#     assert result_save["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
#     assert config_entry.options == options_input

# Note: The XgimiConfigFlow itself is not explicitly patched here, but its methods
# like `async_step_user` are invoked through `hass.config_entries.flow`.
# The `is_host_valid` function is patched within the `custom_components.xgimi.config_flow`
# namespace where it's looked up by the config flow.
# The `hass` fixture is simplified; for full HASS testing, `pytest-homeassistant-custom-component`
# provides a more complete `hass` instance.
# For `test_config_flow_user_step_already_configured`, the actual mechanism involves
# `self.async_set_unique_id()` being called in `async_step_user` before `_abort_if_unique_id_configured()`.
# The first successful flow will register the unique ID. The second flow will detect it.
# The default `_async_current_entries` in `FlowHandler` would list existing config entries.
# The `_abort_if_unique_id_configured` method uses this to check for duplicates.
# My mock for `hass.config_entries.async_entries` is basic; a more robust mock might be needed
# if the flow interacts more deeply with existing entries beyond unique ID checks.
# However, `_abort_if_unique_id_configured` often relies on `self._async_current_ids(include_ignore=False)`
# which is part of the flow handler itself and should work if `async_set_unique_id` has been called.
# The `hass.config_entries.flow.async_configure` for the first entry will effectively "register" it.

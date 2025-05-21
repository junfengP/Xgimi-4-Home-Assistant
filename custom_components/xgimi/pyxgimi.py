import asyncudp
import asyncio
import logging  # Added
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.advert import Advertisement
from time import time

_LOGGER = logging.getLogger(__name__)  # Added


class XgimiApi:
    """Controls XGIMI projectors locally."""  # Added

    def __init__(
        self,
        ip: str,
        command_port: int,
        advance_port: int,
        alive_port: int,
        manufacturer_data: str,
    ) -> None:
        """
        Initializes the XgimiApi.

        Args:
            ip: The IP address of the XGIMI projector.
            command_port: The port for basic commands.
            advance_port: The port for advanced commands.
            alive_port: The port used to check if the projector is alive (e.g., for TCP health check).
            manufacturer_data: Bluetooth LE manufacturer data used for power-on commands.
        """
        _LOGGER.info(
            "Initializing XgimiApi for %s (command: %s, advance: %s, alive: %s)",
            ip,
            command_port,
            advance_port,
            alive_port,
        )  # Added
        self.ip = ip
        self.command_port = command_port  # 16735
        self.advance_port = advance_port  # 16750
        self.alive_port = alive_port  # 554
        self.manufacturer_data = manufacturer_data
        self._is_on = False
        self.last_on = time()
        self.last_off = time()

        # Dictionary mapping simple command names to their raw protocol strings
        self._command_dict = {
            "ok": "KEYPRESSES:49",
            "play": "KEYPRESSES:49",
            "pause": "KEYPRESSES:49",
            "power": "KEYPRESSES:116",
            "back": "KEYPRESSES:48",
            "home": "KEYPRESSES:35",
            "menu": "KEYPRESSES:139",
            "right": "KEYPRESSES:37",
            "left": "KEYPRESSES:50",
            "up": "KEYPRESSES:36",
            "down": "KEYPRESSES:38",
            "volumedown": "KEYPRESSES:114",
            "volumeup": "KEYPRESSES:115",
            "poweroff": "KEYPRESSES:30",
            "volumemute": "KEYPRESSES:113",
            "autofocus": "KEYPRESSES:2099",
            "autofocus_new": "KEYPRESSES:2103",  # Newer models autofocus
            "manual_focus_left": "KEYPRESSES:2097",
            "manual_focus_right": "KEYPRESSES:2098",
            "motor_left_overstep": "KEYPRESSES:2095",
            "motor_left_start": "KEYPRESSES:2092",
            "motor_right_overstep": "KEYPRESSES:2096",
            "motor_right_start": "KEYPRESSES:2093",
            "motor_stop": "KEYPRESSES:2101",
            "shortcut_setting": "KEYPRESSES:2094",
            "choose_source": "KEYPRESSES:2102",
            "hibernate": "KEYPRESSES:2106",  # Enter hibernate mode
            "xmusic": "KEYPRESSES:2108",  # XMusic key / Bluetooth speaker mode
        }
        # Template for advanced commands, 'command_holder' is replaced with the actual command.
        # This structure is based on observed traffic for non-standard key presses.
        self._advance_command = str(
            {
                "action": 20000,
                "controlCmd": {
                    "data": "command_holder",
                    "delayTime": 0,
                    "mode": 5,
                    "time": 0,
                    "type": 0,
                },
                "msgid": "2",
            }
        )

    @property
    def is_on(self) -> bool:
        """Return true if the device is on."""
        return self._is_on

    async def async_fetch_data(self):
        """
        Fetches the latest status of the projector.
        It uses a time-based heuristic for recent power on/off events,
        otherwise performs an active check.
        """
        if (
            time() - self.last_on < 30
        ):  # Optimistic: if recently turned on, assume it's still on
            self._is_on = True
        elif (
            time() - self.last_off < 30
        ):  # Optimistic: if recently turned off, assume it's still off
            self._is_on = False
        else:
            # Perform an active check if the state is uncertain
            alive = await self.async_check_alive()
            self._is_on = alive

    async def async_check_alive(self) -> bool:
        """
        Checks if the projector is alive and reachable by attempting a TCP connection.

        Returns:
            True if the projector is reachable, False otherwise.
        """
        _LOGGER.debug("Checking reachability of %s:%s", self.ip, self.alive_port)
        try:
            # Try to open a connection to the specified port with a short timeout
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.alive_port),
                timeout=2.0,  # Short timeout (2 seconds)
            )
            # If connection succeeds, close it immediately and return True
            writer.close()
            await writer.wait_closed()
            _LOGGER.debug(
                "Successfully connected to %s:%s. Device is alive.",
                self.ip,
                self.alive_port,
            )
            return True
        except asyncio.TimeoutError:
            _LOGGER.debug(
                "Connection to %s:%s timed out. Device is not reachable.",
                self.ip,
                self.alive_port,
            )
            return False
        except ConnectionRefusedError:
            _LOGGER.debug(
                "Connection to %s:%s refused. Device is not reachable.",
                self.ip,
                self.alive_port,
            )
            return False
        except Exception as e:
            # Log any other exceptions and return False
            _LOGGER.warning(
                "An unexpected error occurred while checking reachability of %s:%s: %s",
                self.ip,
                self.alive_port,
                e,
            )
            return False

    async def async_ble_power_on(
        self,
        manufacturer_data: str,
        company_id: int = 0x0046,
        service_uuid: str = "1812",
    ) -> None:
        """
        Sends a Bluetooth Low Energy (BLE) advertisement to power on the projector.

        Args:
            manufacturer_data: The manufacturer-specific data for the BLE advertisement.
                               This is typically a hex string representing device-specific wake-up command.
            company_id: The company ID for the BLE advertisement. Defaults to 0x0046.
            service_uuid: The service UUID for the BLE advertisement. Defaults to "1812" (Human Interface Device).
        """
        _LOGGER.debug(
            "Attempting BLE power on for %s with manufacturer data: %s",
            self.ip,
            manufacturer_data,
        )
        bus = await get_message_bus()
        advert = Advertisement(
            localName="Bluetooth 4.0 RC",  # Common local name for XGIMI remotes
            serviceUUIDs=[service_uuid],
            manufacturerData={
                company_id: bytes.fromhex(manufacturer_data)
            },  # Key part for waking the device
            timeout=1,  # Advertisement timeout
            duration=1000,  # Advertisement duration in ms
            appearance=961,  # HID Keyboard
        )
        try:
            await advert.register(bus)
            _LOGGER.debug("BLE advertisement sent successfully for %s.", self.ip)
        except Exception as e:
            _LOGGER.error("Error registering BLE advertisement for %s: %s", self.ip, e)
            # Re-raise the exception so the caller can handle it if necessary
            raise

    async def async_robust_ble_power_on(
        self,
        manufacturer_data: str,
        company_id: int = 0x0046,
        service_uuid: str = "1812",
    ) -> None:
        """
        Attempts to power on the projector using BLE, retrying multiple times.

        Args:
            manufacturer_data: The manufacturer-specific data for the BLE advertisement.
            company_id: The company ID for the BLE advertisement.
            service_uuid: The service UUID for the BLE advertisement.
        """
        _LOGGER.info("Attempting robust BLE power on for %s.", self.ip)
        success = False
        for i in range(10):  # Retry up to 10 times
            _LOGGER.debug("BLE power on attempt %s/10 for %s.", i + 1, self.ip)
            try:
                await self.async_ble_power_on(
                    manufacturer_data, company_id, service_uuid
                )
                _LOGGER.info(
                    "BLE power on attempt %s/10 succeeded for %s.", i + 1, self.ip
                )
                success = True
                break  # Exit loop on success
            except Exception as e:
                _LOGGER.warning(
                    "BLE power on attempt %s/10 for %s failed: %s. Retrying in 1 second...",
                    i + 1,
                    self.ip,
                    e,
                )
                await asyncio.sleep(1)  # Wait before retrying
        if not success:
            _LOGGER.error("All 10 BLE power on attempts failed for %s.", self.ip)

    async def async_send_command(self, command: str) -> None:
        """
        Sends a command to the XGIMI projector.

        Args:
            command: The command string to send.
                     Can be a predefined key (e.g., "poweroff") or an advanced command string.
        """
        _LOGGER.debug("Attempting to send command '%s' to %s", command, self.ip)
        if command in self._command_dict:
            # Handle standard commands
            if command == "poweroff":
                self._is_on = False  # Optimistically set state
                self.last_off = time()
            msg = self._command_dict[command]
            target_port = self.command_port
            _LOGGER.debug(
                "Sending standard command '%s' (payload: '%s') to %s:%s",
                command,
                msg,
                self.ip,
                target_port,
            )
            try:
                remote_addr = (self.ip, target_port)
                sock = await asyncudp.create_socket(remote_addr=remote_addr)
                sock.sendto(msg.encode("utf-8"))
                sock.close()
                _LOGGER.debug(
                    "Standard command '%s' sent successfully to %s:%s.",
                    command,
                    self.ip,
                    target_port,
                )
            except Exception as e:
                _LOGGER.error(
                    "Error sending standard command '%s' to %s:%s: %s",
                    command,
                    self.ip,
                    target_port,
                    e,
                )

        elif command == "poweron":
            # Handle power on command (uses BLE)
            _LOGGER.info(
                "Executing 'poweron' command for %s using robust BLE method.", self.ip
            )
            self._is_on = True  # Optimistically set state
            self.last_on = time()
            # manufacturer_data is crucial for BLE power on
            await self.async_robust_ble_power_on(self.manufacturer_data)
        else:
            # Handle advanced commands
            msg = self._advance_command.replace("command_holder", command)
            target_port = self.advance_port
            _LOGGER.debug(
                "Sending advanced command (raw: '%s', payload: '%s') to %s:%s",
                command,
                msg,
                self.ip,
                target_port,
            )
            try:
                remote_addr = (self.ip, target_port)
                sock = await asyncudp.create_socket(remote_addr=remote_addr)
                sock.sendto(msg.encode("utf-8"))
                sock.close()
                _LOGGER.debug(
                    "Advanced command '%s' sent successfully to %s:%s.",
                    command,
                    self.ip,
                    target_port,
                )
            except Exception as e:
                _LOGGER.error(
                    "Error sending advanced command '%s' to %s:%s: %s",
                    command,
                    self.ip,
                    target_port,
                    e,
                )
            # Note: It seems there was a bug in the original code where unknown commands would pass through here.
            # However, based on the structure, it's more likely that 'command' here IS the advanced command string.
            # If it were truly an "unknown" command, it should probably be logged as such and not sent.
            # For now, assuming 'command' is the intended advanced payload if not in _command_dict or 'poweron'.

"""Constants for Xgimi Integration."""

# Base component constants
NAME = "Xgimi Projector Integration"
DOMAIN = "xgimi"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.6"

# Port constants
XGIMI_COMMAND_PORT = 16735  # Port for standard remote control commands
XGIMI_ADVANCE_PORT = 16750  # Port for advanced commands / settings
XGIMI_ALIVE_PORT = 554  # Used for RTSP, also for TCP reachability check

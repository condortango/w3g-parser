"""Custom exceptions for W3G parsing."""


class W3GParseError(Exception):
    """Base exception for parsing errors."""

    def __init__(self, message: str, offset: int | None = None):
        self.offset = offset
        super().__init__(f"{message}" + (f" at offset 0x{offset:X}" if offset is not None else ""))


class InvalidHeaderError(W3GParseError):
    """Invalid or unrecognized header format."""

    pass


class UnsupportedVersionError(W3GParseError):
    """Replay version not supported."""

    def __init__(self, version: str):
        super().__init__(f"Unsupported replay version: {version}")
        self.version = version


class DecompressionError(W3GParseError):
    """Failed to decompress data block."""

    pass


class UnknownActionError(W3GParseError):
    """Unknown action type encountered."""

    def __init__(self, action_id: int, offset: int):
        super().__init__(f"Unknown action type 0x{action_id:02X}", offset)
        self.action_id = action_id


class TruncatedDataError(W3GParseError):
    """Data was truncated unexpectedly."""

    pass

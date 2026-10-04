"""Error types Vux raises on purpose, so the CLI can print them nicely."""


class VuxError(Exception):
    """A problem we can explain to the user in one line (no traceback)."""


class UnsupportedPlatformError(VuxError):
    """No backend exists yet for the system Vux is running on."""


class InvalidPackageNameError(VuxError):
    """A package name or search term that is unsafe or malformed."""

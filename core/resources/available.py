def is_available_default() -> bool:
    """Resources are available by default.

    Availability is implicit — no entry is needed to represent it.
    A resource is considered available for any time window unless an
    explicit unavailability entry exists that covers that window.
    """
    return True

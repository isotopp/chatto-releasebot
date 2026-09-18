from importlib.metadata import distribution


def test_console_entry_point_loads() -> None:
    entry_point = next(
        entry_point
        for entry_point in distribution("chatto-releasebot").entry_points
        if entry_point.name == "chatto-releasebot"
    )
    assert callable(entry_point.load())

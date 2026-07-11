# tests/

Test suite for Blender Buddy. Run with `uv run pytest`.

## Conventions
- UI tests drive the app through Textual's headless `App.run_test()` pilot
  harness — never `App.run()` (that needs a real TTY and fails under pytest/CI).
- Tests are `async def`; `asyncio_mode = "auto"` (in `pyproject.toml`) runs them
  without a `@pytest.mark.asyncio` marker.
- `test_app.py` is the boot smoke test (app mounts the dashboard, `q` quits,
  exit code 0). Add feature tests alongside as behavior grows.

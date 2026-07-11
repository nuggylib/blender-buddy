# Blender Buddy

Blender Buddy is a custom tool built by the McNuggies game dev team. It's sole purpose is
verifying Blender assets are fully prepared for export into a game.

This tool is ideal for games with many models of the same class and have a similar (or 
even identical) setup. It was built for use with Godot.

## Features

1. **Custom Spec Generation**
   - _Generate a spec for your model_
   - _Describe the base setup for your model file_
   - _Advises standard naming convention_
   - _Specs drive validation logic_
2. **Armature Validation**
   - _Verify armature exists_
   - _Verify armature has expected bones_
   - _Verify bone parenting is correct_
2. **Mesh Validation**
   - _Verify expected meshes are present_
   - _Verify meshes are linked to the correct bone_
   - _Verify vertex group weights are correct_

## Development

Blender Buddy uses [uv](https://docs.astral.sh/uv/) for dependency and
environment management. Requires Python 3.11+ (uv will fetch it automatically).

```bash
# Install dependencies (runtime + dev) into a local virtual environment
uv sync

# Launch the TUI
uv run blender-buddy
# ...or equivalently
uv run python -m blender_buddy

# Run the test suite
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

During UI development, `uv run textual run --dev blender_buddy.app:BlenderBuddyApp`
enables live CSS editing, and `uv run textual console` (in a second terminal)
captures log output.


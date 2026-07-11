# blender_buddy/tui/

The Textual UI layer: everything the user sees and interacts with.

## Contents
- `screens/` — full-page views (`Screen` subclasses). The app navigates by
  pushing/popping screens on the stack.

## Conventions
- Screens go in `screens/`; reusable widgets get their own `widgets/`
  subpackage (with its own `CLAUDE.md`) when the first one is added.
- Keep presentation here; validation logic and Blender I/O live in their own
  categories and are surfaced to screens via app-level state.

# blender_buddy/tui/screens/

Full-page Textual `Screen` subclasses. Each screen is one landing view or page
in the app (analogous to a route in a web app).

## Contents
- `dashboard.py` — `DashboardScreen`, the landing view. Currently a placeholder;
  future work makes it display live validation results from a Blender-polling
  worker and lets the user open per-category detail screens.

## Conventions
- One screen per file, named `<Name>Screen`.
- Register screens in `BlenderBuddyApp.SCREENS` and navigate with
  `push_screen` / `pop_screen`.

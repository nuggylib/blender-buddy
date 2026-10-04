# blender_buddy/tui/widgets/

Reusable Textual widgets — the parts screens are assembled from. A widget earns
a place here once a *second* screen needs it, or once it carries behavior
(focus, bindings, messages) rather than just layout. One-off layout stays inline
in the screen that owns it.

## Contents
- `section_card.py` — `SectionCard(Vertical, can_focus=True,
  can_focus_children=False)`, one focusable section of a hub screen. Holds
  arbitrary children (the dashboard passes `Static` rows), binds `enter` to an
  action that posts `SectionCard.Opened(target)`, and takes `target` — a name
  registered in `BlenderBuddyApp.SCREENS`, not a screen instance.
  `can_focus_children=False` is load-bearing: it keeps the hub's focus chain at
  exactly **one stop per section**, so a `Button` added inside a card later
  cannot become a stop of its own and break the "arrow keys step through
  sections" contract.

## Conventions
- **A widget never navigates.** It names where it leads (`target`) and posts a
  message; the hub screen handling that message owns `push_screen`. This is what
  keeps a card reusable by any future hub screen and keeps the pushes in one
  place.
- Messages are nested classes on the widget, so Textual derives the handler name
  from the qualname (`SectionCard.Opened` → `on_section_card_opened`).
- Styling lives in `app.tcss` keyed off the classes the screen assigns, not in
  `DEFAULT_CSS` here — a reusable widget shouldn't dictate how each screen
  wants it to look. (`SetupWizard`'s `DEFAULT_CSS` is screen-local layout, a
  different case.)

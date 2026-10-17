# [Textual API](https://textual.textualize.io/api/)

High level (human-written) information about how to implement the Textual API.

## [`App` basics](https://textual.textualize.io/guide/app/)

* Reusable components are "Widgets"
   * Applications should use one or many Widgets to create a user interface
* Possible to use an "inline" mode
* You can also mount Widgets, but composing is preferred
    * It's sometimes necessary to mount Widgets in response to events
    * When you mount a widget, Textual will mount everything the widget composes
        * Textual guarantees that the mounting will be complete by the next message handler...
        * **...but not immediately after the call to `mount()`**

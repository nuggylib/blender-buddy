# Blender Buddy

Blender Buddy is a Python-based TUI aimed at expediting building game models in Blender specifically 
for Godot.

## Project Structure

Although Python does not enforce any sort of hard-and-fast project structure, this project uses a
**flat layout**: all application code lives in the `blender_buddy/` package directory at the repository
root (not under a `src/` directory). The `blender_buddy/` directory _is_ Blender Buddy — everything in
it is packaged together into the published, downloadable Blender Buddy binary.

The repository root also holds `blender-buddy.spec`, the committed PyInstaller build definition (see the
README's "Building a standalone binary"). It is build tooling, not application code — packaging happens
_from_ it, but it is not part of the shipped package.

### Code Organization & Documentation Conventions

1. **Separate code by category within `blender_buddy/`.** Group source files into meaningful category
   subpackages (by domain, feature, or responsibility) rather than placing everything at the top
   level of `blender_buddy/`. When adding new code, put it in the directory that matches its purpose,
   and create a new category directory when none fits.
2. **Write a `CLAUDE.md` whenever a new directory is created** — whether it is a direct child of
   `blender_buddy/` or nested any number of levels below it. Each new directory gets its own
   `CLAUDE.md` describing what the directory holds and any conventions specific to it.
3. **Keep `CLAUDE.md` files current as the project evolves.** When a directory's contents change
   meaningfully (new files, changed responsibilities, new patterns), make a genuine attempt to update
   that directory's `CLAUDE.md` so the documentation stays accurate.

### Feature Development Practices

Keep PRs as small as possible by ensuring each branch is purpose-built for a specific sub-task of a feature.

## General Workflow

> This workflow is intended to fast-track development of many similar models that leverage a similar
> setup. For example, a game with a range of standard vehicles will need a model for each car, but
> each model will have the same core components. That being said, this tool CAN benefit one-off model
> development as well as the checklist is intended to be very comprehensive.

1. User builds a base model in Blender
2. User starts up Blender Buddy
3. User selects (or creates) the spec to use
4. Blender Buddy opens a connection to active Blender scene
5. Blender Buddy shows a live dashboard with simple display of validation results
6. User can select a category to see full details
7. Each full-details page has steps at the bottom for how to fix the issues that can occur
8. As the user makes changes, validation results live-update

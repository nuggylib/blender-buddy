# Running from source

This document covers how to run `model-meta` from source (this codebase).

## System requirements

1. [`uv`](https://docs.astral.sh/uv/) installed
2. Python 3.11 or newer (run `uv python install` in this repo)
3. Blender installed (will work without out it)
4. Godot installed (will work without it)

For Blender and Godot, they are only required if you are leveraging functionality that uses their APIs. Blender is
the most-crucial since the `.blend` files are what's evaluated prior to exporting to Godot.

## First-time setup

1. Clone the repository
2. Run `uv python install`
3. Run `uv sync`

## Running the app

1. Run `uv run model-meta`

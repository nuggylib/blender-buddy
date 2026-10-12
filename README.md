# Model Meta

Model Meta is a custom tool built by the McNuggies game dev team. It's sole purpose is
verifying 3D model game assets are fully prepared for export into a game.

This tool is ideal for games with many models of the same class and have a similar (or 
even identical) setup. It is currently built for use with Godot.

## Running the application

1. Start the application
   - If you've cloned it, run `uv sync` > `uv run model-meta`
   - _(TODO)_ Otherwise, install from Hombebrew and run from the command line
2. Run the setup and configure the Godot and Blender home
3. Add one or more Model directories
4. Add one or more Specs

> **NOTE**: This will be superseded by a usage doc once the tool is in a v1 state

## Inspiration

The reasons why `model-meta` was created.

### Quality-of-life improvements

As aspiring indie game developers, we've been learning the ropes of game development
specifically for 3D games. In many games, there are "classes" of models, including our
own. This means that many of the models will have a nearly-identical file setup. However,
due to the creative nature of 3D modeling, the setup is only part of the problem -
unless you want all of your models to look exactly, the same, you need to customize each
model as-needed for your game's style.

Given enough complexity in your model, it can easily become pretty arduous to ensure
you've fully prepared your model for export into a game engine like Godot. I am sure
there are already many tools out there for the major prorpietary engines, but I am solely
focused on Godot, so I haven't bothered searching further.

### Learning the Blender APIs

I don't normally work in Python, but I am comfortable with it. The Blender APIs are all in
Python, so for the sake of refreshing myself, I am building this tool in Python as well.

### Learning the limitations of Godot

As mentioned above, I am focused solely on building games in Godot. Because of this, there
are significant limitations in how the rendering engine works. On top of this, it also
depends on the rendering engine you choose within the Godot project setup. I am opting
for a flexible spec system for it adaptability as more feature requirements are surfaced.

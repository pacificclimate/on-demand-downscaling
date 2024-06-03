# on-demand-downscaling

This repository contains the workflow for the on-demand downscaling project. The `on-demand_downscaling` directory has the following files:
- A `README.md` describing the goals of the project, how the notebook is structured and should be run, and some additional information
- The notebook itself, called `on_demand_downscaling.ipynb`
- A module called `helpers.py` with helper functions/objects used to set up the widgets used throughout the notebook

## Installation

The dependencies used for this repo are managed using the [poetry](https://python-poetry.org/) tool. You can review [this document](https://confluence.pcic.uvic.ca/pages/viewpage.action?pageId=83919386) to see how to install and use it. After installing it, you can set up the virtual environment and the dependencies by running

```bash
$ poetry install
```

You can then enter the environment by running

```bash
$ poetry shell
```

## Notebook Startup

Once the virtual environment is set up, you can start a Jupyterlab instance by running

```bash
jupyter lab
```

You can then open the notebook from the left sidebar.

## Releasing

Creating a versioned release involves:

1. Incrementing `version` in `pyproject.toml`
2. Summarize the changes from the last release in `NEWS.md`
3. Commit these changes, then tag the release:

```bash
git add pyproject.toml NEWS.md
git commit -m "Bump to version X.X.X"
git tag -a -m "X.X.X" X.X.X
git push --follow-tags
```
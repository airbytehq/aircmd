# Aircmd

Aircmd is an extensible CLI built with Python 3.11 and the Click framework. You can use aircmd to discover and install plugins that extend the functionality of the CLI. 

## Installation

To install aircmd and work with it locally, first make sure you have Python 3.11 and Poetry installed. Then, clone the aircmd repository:

```bash
git clone https://github.com/airbytehq/aircmd.git
cd aircmd
```

Next, create a virtual environment and install the dependencies:

```bash
poetry install
```

Finally, you can run the CLI using the `aircmd` command:

```bash
poetry run aircmd
```

In order to work in development mode and not have to prefix every command with `poetry run aircmd`, it's better to jump into a poetry shell so that you can save that step:

```bash
poetry shell
aircmd --help
```

If you want to be able to run the aircmd command from anywhere without using poetry run, you'll need to modify your system's PATH environment variable to include the venv/bin directory of your project. For development you should avoid this, however, as it will conflict with the global production install of aircmd 

## Plugin Discovery

Aircmd uses a plugin manager to discover plugins. To discover plugins, make sure they are installed in the Python environment that aircmd is running in. You can use the following command to see a list of installed plugins:

```
aircmd plugin list
```

## Installing a Plugin

To install a plugin, you can use the following command:

```
aircmd plugin install airbyte_actions
```

This will install the `airbyte_actions` plugin and make its commands available in aircmd.

## Uninstalling a Plugin

To uninstall a plugin, you can use the following command:

```
aircmd plugin uninstall airbyte_actions
```

This will remove the `airbyte_actions` plugin and its commands from aircmd. 

## Using a Plugin

Once you have installed a plugin, you can use its commands in aircmd. Each plugin should be its own click command group. For example, if you have installed the `airbyte_actions` plugin, you can issue commands like this:

```
aircmd actions command1
```

This will run the `command1` command from the `airbyte_actions` plugin.

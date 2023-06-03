# Aircmd

Aircmd is an extensible command line interface (CLI) that discovers and manages installable plugins to define commands related to developing and operating Airbyte. 

Aircmd makes use of Pydantic for data validation and Click for building the command line interface. You can use aircmd to discover and install plugins that perform various Airbyte related tasks

## Installation

### Quick start

```bash
$ pip install aircmd
```

```bash
$ aircmd
```

### Dependencies

`aircmd` requires SOPS for secrets management and Docker for running pipelines

### Local Development

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

## Configuring `aircmd` with secrets

Configuration is done in the following order:


 1 Load secrets using SOPS and store them in environment variables.                                                                                                   
 2 Load environment variables from .env file using python-dotenv                                                                                                     
 3 Use the GlobalSettings class that inherits from BaseSettings to automatically read the configuration from environment variables. This is an immutable singleton that is created as `aircmd` starts up


To solve the chicken and egg problem (you need to have a secret to decrypt a secret), `aircmd` will use the existing gcloud configuration stored on the machine to attempt to decrypt secrets, or optionally can take in a service account JSON as input to perform this decryption instead

## Plugin Discovery

Aircmd uses a plugin manager to discover plugins. To discover plugins, make sure they are installed in the Python environment that aircmd is running in. You can use the following command to see a list of installed plugins and installable plugins:

```
aircmd plugin list
```

## Installing a Plugin

To install a plugin, you can use the following command:

```
aircmd plugin install airbyte_oss
```

This will install the `airbyte_oss` plugin and make its commands available in aircmd.

## Uninstalling a Plugin

To uninstall a plugin, you can use the following command:

```
aircmd plugin uninstall airbyte_oss
```

This will remove the `airbyte_oss` plugin and its commands from aircmd. 

## Using a Plugin

Once you have installed a plugin, you can use its commands in aircmd. Each plugin should be its own click command group. For example, if you have installed the `airbyte_oss` plugin, you can issue commands like this:

```
aircmd oss command1
```

This will run the `command1` command from the `airbyte_oss` plugin.

import importlib.metadata as metadata

import click


class PluginManager:
    def __init__(self):
        self.plugins = {}

    def discover(self):
        for entry_point in metadata.entry_points().get('aircmd.plugins', []):
            plugin_name = entry_point.name
            try:
                plugin_module = entry_point.load()
            except Exception as e:
                click.echo(f"Failed to load plugin {plugin_name}: {e}")
                continue
            self.plugins[plugin_name] = plugin_module

    def get_command_groups(self):
        command_groups = []
        for plugin in self.plugins.values():
            try:
                command_group = plugin.get_command_group()
            except AttributeError:
                continue
            command_groups.append(command_group)
        return command_groups


@click.group()
@click.pass_context
def cli(ctx):
    if not ctx.obj:
        ctx.obj = {}
    ctx.obj['plugin_manager'] = PluginManager()
    ctx.obj['plugin_manager'].discover()


    for command_group in ctx.obj['plugin_manager'].get_command_groups():
        click.echo(command_group)
        cli.add_command(command_group)

@click.group(name='plugin')
@click.pass_obj
def plugin(obj):
    pass


@plugin.command()
@click.pass_obj
def list(obj):
    """List installed plugins"""
    click.echo("List installed plugins")
    for plugin_name in obj['plugin_manager'].plugins.keys():
        click.echo(plugin_name)


cli.add_command(plugin)

if __name__ == '__main__':
    cli(obj={})

import click

from sceptre.context import SceptreContext
from sceptre.cli.helpers import catch_exceptions
from sceptre.cli.helpers import confirmation
from sceptre.cli.helpers import stack_status_exit_code
from sceptre.plan.plan import SceptrePlan


@click.command(name="launch")
@click.argument("path")
@click.option(
    "-y", "--yes", is_flag=True, help="Assume yes to all questions."
)
@click.pass_context
@catch_exceptions
def launch_command(ctx, path, yes):
    """
    Launch a Stack or StackGroup.

    Launch a Stack or StackGroup for a given config PATH.

    :param path: The path to launch. Can be a Stack or StackGroup.
    :type path: str
    :param yes: A flag to answer 'yes' to all CLI questions.
    :type yes: bool
    """
    context = SceptreContext(
        command_path=path,
        project_path=ctx.obj.get("project_path"),
        user_variables=ctx.obj.get("user_variables"),
        options=ctx.obj.get("options")
    )

    plan = SceptrePlan(context)

    confirmation(plan.launch.__name__, yes, command_path=path)
    responses = plan.launch()
    exit(stack_status_exit_code(responses.values()))

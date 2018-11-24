from uuid import uuid1

import click

from sceptre.context import SceptreContext
from sceptre.cli.helpers import catch_exceptions, confirmation
from sceptre.cli.helpers import write, stack_status_exit_code
from sceptre.cli.helpers import simplify_change_set_description
from sceptre.stack_status import StackChangeSetStatus
from sceptre.plan.plan import SceptrePlan
from sceptre.plan.executor import SceptrePlanExecutor
from sceptre.plan.actions import StackActions
from sceptre.exceptions import StackDoesNotExistError


@click.command(name="update")
@click.argument("path")
@click.option(
    "-c", "--change-set", is_flag=True,
    help="Create a change set before updating."
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Display verbose output."
)
@click.option(
    "-y", "--yes", is_flag=True, help="Assume yes to all questions."
)
@click.pass_context
@catch_exceptions
def update_command(ctx, path, change_set, verbose, yes):
    """
    Update a stack.

    Updates a stack for a given config PATH. Or perform an update via
    change-set when the change-set flag is set.

    :param path: Path to execute the command on.
    :type path: str
    :param change_set: Whether a change set should be created.
    :type change_set: bool
    :param verbose: A flag to print a verbose output.
    :type verbose: bool
    :param yes: A flag to answer 'yes' to all CLI questions.
    :type yes: bool
    """

    context = SceptreContext(
        command_path=path,
        project_path=ctx.obj.get("project_path"),
        user_variables=ctx.obj.get("user_variables"),
        options=ctx.obj.get("options"),
        output_format=ctx.obj.get("output_format")
    )

    plan = SceptrePlan(context)

    if change_set:
        plan.resolve(command=plan.create_change_set.__name__)

        nonexistent_stacks = get_list_of_nonexisting_stacks(plan)

        if nonexistent_stacks:
            write("The following stacks don't exist: %s" % [s.name for s in nonexistent_stacks])
            write("Aborting! Update can alter only existing stacks.")
            exit(1)

        for batch in plan.launch_order:
            change_set_name = "-".join(["change-set", uuid1().hex])
            try:
                e = SceptrePlanExecutor(plan.create_change_set.__name__, [batch])
                e.execute(change_set_name)
                e = SceptrePlanExecutor(plan.wait_for_cs_completion.__name__, [batch])
                statuses = e.execute(change_set_name)
                e = SceptrePlanExecutor(plan.describe_change_set.__name__, [batch])
                descriptions = e.execute(change_set_name)

                for stack in descriptions:
                    d = descriptions[stack]
                    if not verbose:
                        d = simplify_change_set_description(d)
                        if statuses[stack] != StackChangeSetStatus.READY:
                            d = "\n%-50s NO CHANGES\n" % stack.name
                            write(d)
                            continue
                    write(d, context.output_format)

                stacks_to_update = [stack for stack in statuses if statuses[stack] == StackChangeSetStatus.READY]

                if stacks_to_update:
                    if yes or click.confirm("Proceed with stack update of %s?" % [x.name for x in stacks_to_update]):
                        e = SceptrePlanExecutor(plan.execute_change_set.__name__, [stacks_to_update])
                        e.execute(change_set_name)
                    else:
                        exit(1)

            finally:
                executor = SceptrePlanExecutor(plan.delete_change_set.__name__, [batch])
                executor.execute(change_set_name)
    else:
        confirmation("update", yes, command_path=path)
        responses = plan.update()
        exit(stack_status_exit_code(responses.values()))

def get_list_of_nonexisting_stacks(plan):
    nonexistent_stacks = set()
    for batch in plan.launch_order:
        for stack in batch:
            stack_actions = StackActions(stack)
            try:
                stack_actions._get_status()
            except StackDoesNotExistError:
                nonexistent_stacks.add(stack)
    return nonexistent_stacks

from __future__ import unicode_literals, division, absolute_import
from builtins import *  # pylint: disable=unused-import, redefined-builtin

from argparse import ArgumentParser, ArgumentTypeError
import re

from sqlalchemy.orm.exc import NoResultFound

from flexget import options
from flexget.event import event
from flexget.terminal import TerminalTable, TerminalTableError, table_parser, console
from flexget.utils.database import Session
from flexget.plugins.list.regexp_list import get_regexp_lists, get_list_by_exact_name, get_regexps_by_list_id, \
    get_regexp, create_list, add_to_list_by_name


def do_cli(manager, options):
    """Handle irc cli"""
    action_map = {
        'all': action_all,
        'list': action_list,
        'add': action_add,
        'del': action_del,
        'purge': action_purge
    }

    action_map[options.regexp_action](options)


def action_all(options):
    """ Show all regexp lists """
    lists = get_regexp_lists()
    header = ['#', 'List Name']
    table_data = [header]
    for regexp_list in lists:
        table_data.append([regexp_list.id, regexp_list.name])
    table = TerminalTable(options.table_type, table_data)
    try:
        console(table.output)
    except TerminalTableError as e:
        console('ERROR: %s' % str(e))


def action_list(options):
    """List regexp list"""
    with Session() as session:
        try:
            regexp_list = get_list_by_exact_name(options.list_name)
        except NoResultFound:
            console('Could not find regexp list with name {}'.format(options.list_name))
            return
        header = ['Regexp']
        table_data = [header]
        regexps = get_regexps_by_list_id(regexp_list.id, order_by='added', descending=True, session=session)
        for regexp in regexps:
            regexp_row = [regexp.regexp or '']
            table_data.append(regexp_row)
        table = TerminalTable(options.table_type, table_data)
        try:
            console(table.output)
        except TerminalTableError as e:
            console('ERROR: %s' % str(e))


def action_add(options):
    with Session() as session:
        regexp_list = get_list_by_exact_name(options.list_name)
        if not regexp_list:
            console('Could not find regexp list with name {}, creating'.format(options.list_name))
            regexp_list = create_list(options.list_name, session=session)

        regexp = get_regexp(list_id=regexp_list.id, regexp=options.regexp, session=session)
        if not regexp:
            console("Adding regexp {} to list {}".format(options.regexp, regexp_list.name))
            add_to_list_by_name(regexp_list.name, options.regexp, session=session)
            console('Successfully added regexp {} to regexp list {} '.format(options.regexp, regexp_list.name))
        else:
            console("Regexp {} already exists in list {}".format(options.regexp, regexp_list.name))


def action_del(options):
    with Session() as session:
        regexp_list = get_list_by_exact_name(options.list_name)
        if not regexp_list:
            console('Could not find regexp list with name {}'.format(options.list_name))
            return
        regexp = get_regexp(list_id=regexp_list.id, regexp=options.regexp, session=session)
        if regexp:
            console('Removing regexp {} from list {}'.format(options.regexp, options.list_name))
            session.delete(regexp)
        else:
            console('Could not find regexp {} in list {}'.format(options.movie_title, options.list_name))
            return


def action_purge(options):
    with Session() as session:
        try:
            regexp_list = get_list_by_exact_name(options.list_name)
        except NoResultFound:
            console('Could not find regexp list with name {}'.format(options.list_name))
            return
        console('Deleting list %s' % options.list_name)
        session.delete(regexp_list)


def regexp_type(regexp):
    try:
        re.compile(regexp)
        return regexp
    except re.error as e:
        raise ArgumentTypeError(e)


@event('options.register')
def register_parser_arguments():
    # Common option to be used in multiple subparsers
    regexp_parser = ArgumentParser(add_help=False)
    regexp_parser.add_argument('regexp', type=regexp_type, help="The regexp")

    list_name_parser = ArgumentParser(add_help=False)
    list_name_parser.add_argument('list_name', nargs='?', help='Name of regexp list to operate on')
    # Register subcommand
    parser = options.register_command('regexp-list', do_cli, help='View and manage regexp lists')
    # Set up our subparsers
    subparsers = parser.add_subparsers(title='actions', metavar='<action>', dest='regexp_action')
    subparsers.add_parser('all', parents=[table_parser], help='Shows all existing regexp lists')
    subparsers.add_parser('list', parents=[list_name_parser, table_parser], help='List regexp from a list')
    subparsers.add_parser('add', parents=[list_name_parser, regexp_parser], help='Add a regexp to a list')
    subparsers.add_parser('del', parents=[list_name_parser, regexp_parser], help='Remove a regexp from a list')
    subparsers.add_parser('purge', parents=[list_name_parser], help='Removes an entire list. Use with caution!')

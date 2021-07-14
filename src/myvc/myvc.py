#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/11 18:17
from docopt import docopt
import questionary
from myvc.methods import Persistence
from myvc.utils import is_port_in_use
import myvc.methods as myvc_methods


def not_empty_text_validator(text):
    return True if len(text) > 0 else "Please enter a value"


def input_text(title):
    text = questionary.text(
        title, validate=not_empty_text_validator
    ).ask()
    if text is None:
        exit(0)
    return text


def port_validator(port):
    try:
        port = int(port)
    except Exception as e:
        return "port should be a int value, {}".format(e)
    if not (0 < port < 65535):
        return "port should between {}~{}".format(0, 65535)
    if is_port_in_use(port):
        return "port {} is in using".format(port)
    return True


def select_db():
    _ = questionary.select(
        "Please select a db",
        choices=[
            questionary.Choice(title='{}[{}]'.format(db.name, db.id), value=db.id)
            for db in myvc_methods.dbs.dbs
        ]
    ).ask()
    if _ is None:
        exit(0)
    return _


def select_branch(db_id):
    db_info = myvc_methods.dbs.get_db_info_by_id(db_id)
    choices = []
    for branch in db_info.version.get_self_and_all_children_objects():
        title = '{}[{}({})]'.format(
            '   ' * branch.depth, branch.volume, branch.name
        )
        title = '{0}{1}'.format(title, str(branch.create_at).rjust(80 - len(title), '┈'))
        choices.append(
            questionary.Choice(
                title=title, value=branch.volume,
                checked=branch.volume == db_info.current_version
            )
        )
    _ = questionary.select(
        "Please select a branch", choices=choices
    ).ask()
    if _ is None:
        exit(0)
    return _


doc = '''
MySQL Version Control

Usage:
    myvc ls
    myvc show db
    myvc new db
    myvc start db
    myvc stop db
    myvc rm db
    myvc new branch
    myvc use branch
    myvc copy branch
    myvc clear branch
    myvc rm branch
    myvc run sql
    myvc reset db conf
'''


def main():
    arguments = docopt(doc)
    with Persistence():
        if arguments['ls']:
            myvc_methods.list_dbs()
        elif arguments['show'] and arguments['db']:
            db_id = select_db()
            myvc_methods.db_detail(db_id)
        elif arguments['start'] and arguments['db']:
            db_id = select_db()
            myvc_methods.start_db(db_id)
        elif arguments['stop'] and arguments['db']:
            db_id = select_db()
            myvc_methods.stop_db(db_id)
        elif arguments['rm'] and arguments['db']:
            db_id = select_db()
            myvc_methods.rm_db(db_id)
        elif arguments['new'] and arguments['db']:
            answers = questionary.form(
                name=questionary.text(
                    "DB's name", validate=not_empty_text_validator
                ),
                port=questionary.text(
                    "DB's port", validate=port_validator
                ),
                password=questionary.password("DB's password")
            ).ask()
            if not answers:
                exit(0)
            db_id = myvc_methods.new_db(answers['name'], int(answers['port']), answers['password'])
            myvc_methods.db_detail(db_id)
        elif arguments['new'] and arguments['branch']:
            db_id = select_db()
            name = input_text("Branch's name")
            branch = select_branch(db_id)
            myvc_methods.backup_version(db_id, name, branch)
        elif arguments['use'] and arguments['branch']:
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.apply_version(db_id, branch)
        elif arguments['copy'] and arguments['branch']:
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.copy_from(db_id, branch)
        elif arguments['clear'] and arguments['branch']:
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.clean_data(db_id, branch)
        elif arguments['rm'] and arguments['branch']:
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.rm_version(db_id, branch)
        elif arguments['run'] and arguments['sql']:
            db_id = select_db()
            sql_path = questionary.path("SQL file path").ask()
            if not sql_path:
                exit(0)
            db_name = questionary.text("Database name (Optional)").ask()
            if db_name is None:
                exit(0)
            myvc_methods.apply_sql(db_id, sql_path, db_name)
        elif arguments['reset'] and arguments['db'] and arguments['conf']:
            db_id = select_db()
            db_info = myvc_methods.dbs.get_db_info_by_id(db_id)
            myvc_methods.stop_db(db_id)
            myvc_methods.init_mysql_conf_volume(db_info.conf_volume)
            myvc_methods.start_db(db_id)


if __name__ == '__main__':
    main()

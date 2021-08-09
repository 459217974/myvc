#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/11 18:17
from collections import OrderedDict
import questionary
import pymysql
from myvc_app.methods import Persistence
from myvc_app.utils import is_port_in_use
import myvc_app.methods as myvc_methods


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


def select_db(require_db_is_running=False):
    db_id = questionary.select(
        "Please select a db",
        choices=[
            questionary.Choice(title='{}[{}]'.format(db.name, db.id), value=db.id)
            for db in myvc_methods.dbs.dbs
        ]
    ).ask()
    if db_id is None:
        exit(0)
    if require_db_is_running:
        myvc_methods.check_is_running(db_id)
    return db_id


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


def select_mysql_database(db_id):
    db_info, container = myvc_methods.check_is_running(db_id)

    connection = pymysql.connect(
        host='localhost',
        port=db_info.port,
        user='root',
        password=db_info.password,
        cursorclass=pymysql.cursors.DictCursor
    )
    with connection.cursor() as cursor:
        cursor.execute("SHOW DATABASES;")
        result = cursor.fetchall()

    database_name = questionary.autocomplete(
        'Database name (Optional)',
        choices=[r['Database'] for r in result]
    ).ask()
    return database_name


def select_commands():
    commands = OrderedDict({
        'ls': "show all existed db",
        'show db': "show a db's detail",
        'new db': "create a db",
        'start db': "start a db",
        'stop db': "stop a db",
        'rm db': "delete a db's all data",
        'new branch': "create a db's data branch",
        'use branch': "apply a branch",
        'copy branch': "copy a branch's data to current branch",
        'clear branch': "clear current branch's data",
        'rm branch': "delete a branch and it's children",
        'run sql': "execute a sql file",
        'reset db conf': "replace mysql conf by .cny files in config directory",
        'db shell': "get mysql shell"
    })
    command = questionary.autocomplete(
        'Enter your command',
        choices=list(commands.keys()),
        meta_information=commands,
        validate=lambda x: x in commands
    ).ask()
    return command


def main():
    with Persistence():
        command = select_commands()
        if command == 'ls':
            myvc_methods.list_dbs()
        elif command == 'show db':
            db_id = select_db()
            myvc_methods.db_detail(db_id)
        elif command == 'start db':
            db_id = select_db()
            myvc_methods.start_db(db_id)
        elif command == 'stop db':
            db_id = select_db()
            myvc_methods.stop_db(db_id)
        elif command == 'rm db':
            db_id = select_db()
            myvc_methods.rm_db(db_id)
        elif command == 'new db':
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
        elif command == 'new branch':
            db_id = select_db()
            name = input_text("Branch's name")
            branch = select_branch(db_id)
            auto_switch_to_new_branch = questionary.confirm(
                'Auto switch to the new branch? ({})'.format(name)
            ).ask()
            new_branch_volume_id = myvc_methods.backup_version(db_id, name, branch)
            if auto_switch_to_new_branch:
                myvc_methods.apply_version(db_id, new_branch_volume_id)
        elif command == 'use branch':
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.apply_version(db_id, branch)
        elif command == 'copy branch':
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.copy_from(db_id, branch)
        elif command == 'clear branch':
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.clean_data(db_id, branch)
        elif command == 'rm branch':
            db_id = select_db()
            branch = select_branch(db_id)
            myvc_methods.rm_version(db_id, branch)
        elif command == 'run sql':
            db_id = select_db(require_db_is_running=True)
            sql_path = questionary.path("SQL file path").ask()
            if not sql_path:
                exit(0)
            db_name = select_mysql_database(db_id)
            if db_name is None:
                exit(0)
            myvc_methods.apply_sql(db_id, sql_path, db_name)
        elif command == 'reset db conf':
            db_id = select_db()
            db_info = myvc_methods.dbs.get_db_info_by_id(db_id)
            myvc_methods.stop_db(db_id)
            myvc_methods.init_mysql_conf_volume(db_info.conf_volume)
            myvc_methods.start_db(db_id)
        elif command == 'db shell':
            db_id = select_db(require_db_is_running=True)
            myvc_methods.db_shell(db_id)


if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/11 18:17
import datetime
import json
import os
import subprocess
from collections import OrderedDict
import argparse
from tempfile import NamedTemporaryFile
from typing import Union

import questionary
import pymysql
from pymysql.cursors import DictCursor
from tabulate import tabulate

from myvc_app import init  # This import is to complete some initialization operations
from myvc_app.models.base import DB
from myvc_app.models.models import DBInfo, DataVersion, Config, MySQLConf
from myvc_app.utils import is_port_in_use
import myvc_app.methods as myvc_methods


def not_empty_text_validator(text: str) -> bool:
    return True if len(text) > 0 else "Please enter a value"


def input_text(title: str) -> str:
    text = questionary.text(
        title, validate=not_empty_text_validator
    ).ask()
    if text is None:
        exit(0)
    return text


def port_validator(port: int) -> Union[bool, str]:
    try:
        port = int(port)
    except Exception as e:
        return "port should be a int value, {}".format(e)
    if not (0 < port < 65535):
        return "port should between {}~{}".format(0, 65535)
    if is_port_in_use(port):
        return "port {} is in using".format(port)
    return True


def select_db(require_db_is_running: bool = False) -> int:
    db_id = questionary.select(
        "Please select a db",
        choices=[
            questionary.Choice(title='[{}] {}'.format(db.id, db.name), value=db.id)
            for db in DBInfo.select()
        ]
    ).ask()
    if db_id is None:
        exit(0)
    if require_db_is_running:
        myvc_methods.check_is_running(db_id)
    return db_id


def select_version(db_id: int):
    db_info = DBInfo.get(id=db_id)  # type: DBInfo
    choices = []
    for version in db_info.root_version.children_tree_objects:
        title = '{}[{}({})]'.format(
            '   ' * version.depth, version.volume, version.name
        )
        title = '{0}{1}'.format(title, str(version.create_at).rjust(80 - len(title), '┈'))
        choices.append(
            questionary.Choice(
                title=title, value=version.id,
                checked=version == db_info.current_version
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
    )
    with connection.cursor(DictCursor) as cursor:
        cursor.execute("SHOW DATABASES;")
        result = cursor.fetchall()

    database_name = questionary.autocomplete(
        'Database name (Optional)',
        choices=[r['Database'] for r in result]
    ).ask()
    return database_name


def list_dbs():
    print(
        tabulate(
            [[db.id, db.name, db.port, db.create_at, db.update_at] for db in DBInfo.select()],
            headers=['ID', 'Name', 'Port', 'Create At', 'Update At']
        )
    )


def db_detail(db_id):
    db_info = DBInfo.get(id=db_id)  # type: DBInfo
    current_version = db_info.current_version  # type: DataVersion
    print('\n')
    print(
        tabulate(
            [[
                db_info.id, db_info.name, db_info.port, '{}({})'.format(current_version.volume, current_version.name),
                db_info.create_at, db_info.update_at
            ]],
            ['ID', 'Name', 'Port', 'Current Version', 'Create At', 'Update At']
        )
    )
    print('\n')
    print(
        tabulate(
            [[str(db_info.root_version.children_tree)]],
            headers=['Versions']
        )
    )
    print('\n')


def list_versions(db_id):
    db_info = DBInfo.get(id=db_id)  # type: DBInfo
    print(db_info.root_version.children_tree)


def edit_config():
    old_configs = {}
    for c in Config.select():
        old_configs[c.key] = c.value
    with NamedTemporaryFile(buffering=0, suffix='.myvc_cfg', delete=False) as temp_cfg_file:
        temp_cfg_file.write(
            json.dumps(
                old_configs, ensure_ascii=False, indent=2
            ).encode('utf8')
        )

    try:
        editor = os.environ['EDITOR']
    except KeyError:
        editor = 'vim'
    r = subprocess.call([editor, temp_cfg_file.name])
    if r != 0:
        raise RuntimeError('call editor failed, exit code: {}'.format(r))
    with open(temp_cfg_file.name, 'rb') as f:
        new_configs = json.load(f)
        with DB.atomic():
            for k, v in new_configs.items():
                if k in old_configs:
                    if v != old_configs[k]:
                        c = Config.get(key=k)
                        c.value = v
                        c.save()
                else:
                    Config(
                        key=k, value=v,
                        create_at=datetime.datetime.now()
                    ).save()
            for k in set(old_configs.keys()) - set(new_configs.keys()):
                Config.delete().where(Config.key == k)
    os.remove(temp_cfg_file.name)


def edit_mysql_conf():
    with NamedTemporaryFile(buffering=0, suffix='.myvc_mysql_cnf', delete=False) as temp_cnf_file:
        conf = MySQLConf.select().order_by(MySQLConf.id).first()  # type: MySQLConf
        temp_cnf_file.write(conf.content.encode('utf8'))

    try:
        editor = os.environ['EDITOR']
    except KeyError:
        editor = 'vim'
    r = subprocess.call([editor, temp_cnf_file.name])
    if r != 0:
        raise RuntimeError('call editor failed, exit code: {}'.format(r))
    with open(temp_cnf_file.name, 'rb') as f:
        conf.content = f.read().decode('utf8')
        conf.save()
    os.remove(temp_cnf_file.name)


def select_commands(command_from_cmd_line=None):
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
        'db shell': "get mysql shell",
        'edit config': "edit myvc configs",
        'edit mysql conf': "edit mysql conf",
    })
    if command_from_cmd_line in commands:
        return command_from_cmd_line
    command = questionary.select(
        'Choice a command',
        choices=[
            questionary.Choice(title='[{}] {}'.format(k, v), value=k)
            for k, v in commands.items()
        ],
        use_shortcuts=True
    ).ask()
    if command is None:
        exit(0)
    return command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='*')
    args = parser.parse_args()
    command = select_commands(' '.join(args.command).strip())
    if command == 'ls':
        list_dbs()
    elif command == 'show db':
        db_id = select_db()
        db_detail(db_id)
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
        db_detail(db_id)
    elif command == 'new branch':
        db_id = select_db()
        name = input_text("Branch's name")
        version = select_version(db_id)
        auto_switch_to_new_branch = questionary.confirm(
            'Auto switch to the new branch? ({})'.format(name)
        ).ask()
        new_version = myvc_methods.backup_version(db_id, name, version)
        if auto_switch_to_new_branch:
            myvc_methods.apply_version(db_id, new_version.id)
    elif command == 'use branch':
        db_id = select_db()
        version = select_version(db_id)
        myvc_methods.apply_version(db_id, version)
    elif command == 'copy branch':
        db_id = select_db()
        version = select_version(db_id)
        myvc_methods.copy_from(db_id, version)
    elif command == 'clear branch':
        db_id = select_db()
        version = select_version(db_id)
        myvc_methods.clean_data(db_id, version)
    elif command == 'rm branch':
        db_id = select_db()
        version = select_version(db_id)
        myvc_methods.rm_version(db_id, version)
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
        db_info = DBInfo.get(id=db_id)
        myvc_methods.stop_db(db_id)
        myvc_methods.init_mysql_conf_volume(myvc_methods.get_volume_by_name(db_info.conf_volume))
        myvc_methods.start_db(db_id)
    elif command == 'db shell':
        db_id = select_db(require_db_is_running=True)
        myvc_methods.db_shell(db_id)
    elif command == 'edit config':
        edit_config()
    elif command == 'edit mysql conf':
        edit_mysql_conf()


if __name__ == '__main__':
    main()

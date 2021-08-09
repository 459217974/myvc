#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/6/30 13:55
import os
import docker
import tarfile
import questionary
from io import BytesIO
from docker.models.containers import Container
from docker.errors import NotFound
from tabulate import tabulate
from myvc_app.data_version import DataVersion
from myvc_app.db_info import DBInfo
from myvc_app.dbs import DBs
from myvc_app.utils import get_id, is_port_in_use, get_current_datetime_str
from myvc_app.config import MYSQL_IMAGE_NAME, MYSQL_VERSION, CONF_D_PATH

client = docker.from_env()
dbs = None  # type: DBs


def get_mysql_image():
    name = '{}:{}'.format(MYSQL_IMAGE_NAME, MYSQL_VERSION)
    if not client.images.list(name=name):
        client.images.pull(MYSQL_IMAGE_NAME, MYSQL_VERSION)
    return client.images.get(name=name)


def get_volume_by_name(name):
    v = None
    try:
        v = client.volumes.get(name)
    except docker.errors.NotFound:
        pass
    return v


def rm_volume_by_name(name):
    v = get_volume_by_name(name)
    if v:
        v.remove()


def get_container_by_name(name) -> Container:
    containers = list(
        filter(
            lambda c: c.name == name,
            client.containers.list()
        )
    )
    return containers[0] if containers else None


def check_is_running(db_id):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    if not db_info.container_id:
        raise Exception("{} don't have running container".format(db_info.name))
    container = client.containers.get(db_info.container_id)  # type: Container
    if container.status != 'running':
        raise Exception("{}'s container is not running".format(db_info.name))
    return db_info, container


def send_file(container: Container, file_path, container_path):
    temp_file = BytesIO()
    zip_sql = tarfile.TarFile(fileobj=temp_file, mode='w')
    zip_sql.add(file_path, arcname=os.path.basename(file_path))
    zip_sql.close()
    temp_file.seek(0)
    container.put_archive(container_path, temp_file.read())


def init_mysql_conf_volume(volume=None):
    if not volume:
        volume = client.volumes.create(get_id())
    else:
        _ = get_volume_by_name(volume)
        assert _, 'volume {} not exists'.format(volume)
        volume = _

    if os.path.exists(CONF_D_PATH):
        image = get_mysql_image()
        temp_name = get_id()
        client.containers.run(
            image, name=temp_name,
            command='bash',
            remove=True,
            volumes={
                volume.name: {'bind': '/etc/mysql/configs', 'mode': 'rw'}
            },
            detach=True, stdout=True, stderr=True, tty=True
        )
        container = get_container_by_name(temp_name)
        for path, _, file_names in os.walk(CONF_D_PATH):
            for file_name in file_names:
                if not file_name.endswith('cnf'):
                    continue
                send_file(container, os.path.join(path, file_name), '/etc/mysql/conf.d/')
        container.stop()
    return volume


def copy_volume(from_volume, to_volume):
    image = get_mysql_image()
    temp_name = get_id()
    c = client.containers.run(
        image, name=temp_name,
        command='bash -c "rm -rf /data/to/* && cp -a /data/from/* /data/to/"',
        remove=True,
        volumes={
            from_volume: {'bind': '/data/from', 'mode': 'rw'},
            to_volume: {'bind': '/data/to', 'mode': 'rw'}
        },
        detach=True
    )  # type: Container
    c.wait(condition='removed')


def clean_volume(volume):
    image = get_mysql_image()
    temp_name = get_id()
    c = client.containers.run(
        image, name=temp_name,
        command='bash -c "rm -rf /data/*"',
        remove=True,
        volumes={
            volume: {'bind': '/data', 'mode': 'rw'},
        },
        detach=True
    )  # type: Container
    c.wait(condition='removed')


def init_container(db_info: DBInfo):
    if is_port_in_use(db_info.port):
        raise Exception('the port {} is in use.'.format(db_info.port))

    image = get_mysql_image()

    client.containers.run(
        image, name=db_info.id,
        volumes={
            db_info.conf_volume: {'bind': '/etc/mysql/conf.d', 'mode': 'rw'},
            db_info.current_version: {'bind': '/var/lib/mysql', 'mode': 'rw'},
        },
        ports={'3306/tcp': db_info.port},
        environment={'MYSQL_ROOT_PASSWORD': db_info.password},
        detach=True,
    )
    container = get_container_by_name(db_info.id)
    db_info.container_id = container.id
    db_info.start_at = get_current_datetime_str()


def new_db(name, port, password):
    db_info = DBInfo()
    dbs.dbs.append(db_info)

    db_info.name = name
    db_info.port = port
    db_info.password = password

    conf_volume = init_mysql_conf_volume()
    db_info.conf_volume = conf_volume.id

    data_volume = client.volumes.create(get_id())
    volume_version = DataVersion(data_volume.id)
    volume_version.name = 'Init {}'.format(name)
    volume_version.create_at = get_current_datetime_str()
    db_info.version = volume_version
    db_info.current_version = volume_version.volume
    db_info.create_at = get_current_datetime_str()

    try:
        init_container(db_info)
        return db_info.id
    except Exception:
        conf_volume.remove()
        data_volume.remove()
        raise


def rm_db(db_id):
    stop_db(db_id)
    db_info = dbs.get_db_info_by_id(db_id)
    if db_info:
        for v in db_info.version.get_self_and_all_children():
            rm_volume_by_name(v)
        rm_volume_by_name(db_info.conf_volume)
    dbs.delete_db_info_by_id(db_id)


def rm_version(db_id, volume):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    if volume == db_info.current_version:
        raise Exception("Can't rm using version")
    if volume == db_info.version.volume:
        raise Exception("Can't rm root version")
    version = db_info.version.get_version_by_volume(volume)
    if not version:
        raise Exception("{} don't have this version {}".format(db_info.name, volume))
    if db_info.current_version in version.get_self_and_all_children():
        raise Exception("using version is {}'s child".format(volume))
    if version.children:
        answer = questionary.confirm(
            'version [{}({})] has children\n\n{}\n\nwill delete all these versions, please confirm.'.format(
                version.volume, version.name, version
            )
        ).ask()
        if not answer:
            return

    version.parent.remove_child(version.volume)
    for v in version.get_self_and_all_children():
        rm_volume_by_name(v)


def clean_data(db_id, volume=None):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    if not volume and not db_info.current_version:
        raise Exception("{} don't have using version".format(db_info.name))
    volume = volume if volume else db_info.current_version
    version = db_info.version.get_version_by_volume(volume)
    if not version:
        raise Exception("db {} don't have this version {}".format(db_info.name, volume))
    v = get_volume_by_name(volume)
    if not v:
        raise Exception("version {} not exists".format(v.name))
    if volume == db_info.current_version:
        stop_db(db_id)
    clean_volume(v.name)
    if volume == db_info.current_version:
        start_db(db_id)


def stop_db(db_id):
    db_info = dbs.get_db_info_by_id(db_id)
    if db_info and db_info.container_id:
        try:
            container = client.containers.get(db_info.container_id)  # type: Container
            container.stop()
            container.remove()
            db_info.stop_at = get_current_datetime_str()
            db_info.container_id = None
        except NotFound:
            pass
    possible_container = get_container_by_name(db_id)
    if possible_container:
        possible_container.kill()
        possible_container.remove()
        if db_info:
            db_info.container_id = None


def start_db(db_id):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    current_data_volume = get_volume_by_name(db_info.current_version)
    if not current_data_volume:
        raise Exception("{}'s current data version {} not exists".format(db_info.name, db_info.current_version))
    conf_volume = get_volume_by_name(db_info.conf_volume)
    if not conf_volume:
        raise Exception("{}'s conf volume not exists".format(db_info.name))
    stop_db(db_id)
    init_container(db_info)


def apply_version(db_id, volume):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    v = db_info.version.get_version_by_volume(volume)
    assert v, "{} don't have this version: {}".format(db_info.name, volume)

    stop_db(db_id)

    db_info.current_version = v.volume
    init_container(db_info)


def copy_from(db_id, from_volume):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    current_v = get_volume_by_name(db_info.current_version)
    assert current_v, "{}'s using version {} not exists".format(db_info.name, db_info.current_version)
    from_v = get_volume_by_name(from_volume)
    assert from_v, "volume {} not exists".format(from_volume)
    stop_db(db_id)
    copy_volume(from_v.name, current_v.name)
    start_db(db_id)


def apply_sql(db_id, sql_path, database_name=None):
    sql_path = os.path.expanduser(sql_path)
    if not os.path.exists(sql_path):
        raise Exception('{} not exists'.format(sql_path))
    sql_path = os.path.abspath(sql_path)
    db_info, container = check_is_running(db_id)
    send_file(container, sql_path, '/')
    if database_name:
        print(container.exec_run(
            "bash -c 'exec mysql -u root -p{} -D {} < \"/{}\"'".format(
                db_info.password, database_name, os.path.basename(sql_path)
            )
        ).output.decode())
    else:
        print(container.exec_run(
            "bash -c 'exec mysql -u root -p{} < \"/{}\"'".format(db_info.password, os.path.basename(sql_path))
        ).output.decode())


def backup_version(db_id, name, volume=None):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    if volume:
        v = db_info.version.get_version_by_volume(volume)
        assert v, "{} don't have this version: {}".format(db_info.name, volume)
    else:
        v = db_info.version.get_version_by_volume(db_info.current_version)
        assert v, "Can't find {}'s current version {}".format(db_info.name, db_info.current_version)

    if volume == db_info.current_version:
        stop_db(db_id)

    backup_volume = client.volumes.create(get_id())
    volume_version = DataVersion(backup_volume.id)
    volume_version.name = name
    volume_version.create_at = get_current_datetime_str()
    v.add_child(volume_version)
    copy_volume(v.volume, backup_volume.id)

    if volume == db_info.current_version:
        start_db(db_id)

    return backup_volume.id


def list_dbs():
    print(
        tabulate(
            [[db.id, db.name, db.port, db.create_at, db.start_at, db.stop_at] for db in dbs.dbs],
            headers=['ID', 'Name', 'Port', 'Create At', 'Start At', 'Stop At']
        )
    )


def db_detail(db_id):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    current_v = db_info.version.get_version_by_volume(db_info.current_version)
    print('\n')
    print(
        tabulate(
            [[
                db_info.id, db_info.name, db_info.port, '{}({})'.format(current_v.volume, current_v.name),
                db_info.create_at, db_info.start_at, db_info.stop_at
            ]],
            ['ID', 'Name', 'Port', 'Current Version', 'Create At', 'Start At', 'Stop At']
        )
    )
    print('\n')
    print(
        tabulate(
            [[str(db_info.version)]],
            headers=['Versions']
        )
    )
    print('\n')


def list_versions(db_id):
    db_info = dbs.get_db_info_by_id(db_id)
    if not db_info:
        raise Exception('{} not exists'.format(db_id))
    print(db_info.version)


def db_shell(db_id):
    db_info, container = check_is_running(db_id)
    os.system(
        "docker exec -it {} bash -c 'mysql -u root -p{}'".format(
            db_info.container_id, db_info.password
        )
    )


class Persistence:

    def __enter__(self):
        global dbs
        dbs = DBs.load()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            dbs.save()

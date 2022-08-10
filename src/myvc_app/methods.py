#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/6/30 13:55
import os
from pathlib import Path
from typing import Union

import docker
import tarfile
import gzip
import questionary
from io import BytesIO
from tempfile import NamedTemporaryFile
from docker.models.containers import Container
from docker.errors import NotFound
from docker.models.images import Image
from docker.models.volumes import Volume

from myvc_app.models.base import DB
from myvc_app.models.models import DBInfo, DataVersion, MySQLConf, Config
from myvc_app.utils import get_id, is_port_in_use

DOCKER_CLIENT_BASE_URL = Config.get_or_none(key='DOCKER_CLIENT_BASE_URL')  # type: Config
if DOCKER_CLIENT_BASE_URL:
    client = docker.DockerClient(DOCKER_CLIENT_BASE_URL.value)
else:
    client = docker.DockerClient.from_env()


def get_mysql_image() -> Image:
    mysql_image_name = Config.get(key='MYSQL_IMAGE_NAME')  # type: Config
    mysql_version = Config.get(key='MYSQL_VERSION')  # type: Config
    name = '{}:{}'.format(mysql_image_name.value, mysql_version.value)
    if not client.images.list(name=name):
        client.images.pull(mysql_image_name.value, mysql_version.value)
    return client.images.get(name=name)


def get_volume_by_name(name: str) -> Volume:
    v = None
    try:
        v = client.volumes.get(name)
    except docker.errors.NotFound:
        pass
    return v


def rm_volume_by_name(name: str):
    v = get_volume_by_name(name)
    if v:
        v.remove()


def get_container_by_name(name: str) -> Container:
    containers = list(
        filter(
            lambda c: c.name == name,
            client.containers.list()
        )
    )
    return containers[0] if containers else None


def check_is_running(db_id: int) -> (DBInfo, Container):
    db_info = DBInfo.get(id=db_id)
    if not db_info.container_id:
        raise Exception("{} don't have running container".format(db_info.name))
    container = client.containers.get(db_info.container_id)  # type: Container
    if container.status != 'running':
        raise Exception("{}'s container is not running".format(db_info.name))
    return db_info, container


def send_file(
        container: Container, file_or_path: Union[Path, str],
        file_name: Union[Path, str], container_path: Union[Path, str]
):
    temp_file = BytesIO()
    zip_sql = tarfile.TarFile(fileobj=temp_file, mode='w')
    zip_sql.add(file_or_path, arcname=Path(file_name).name)
    zip_sql.close()
    temp_file.seek(0)
    container.put_archive(container_path, temp_file.read())


def init_mysql_conf_volume(volume: Volume = None, conf_name: str = None) -> Volume:
    if not volume:
        volume = client.volumes.create(get_id())
    else:
        clean_volume(volume)

    if not conf_name:
        conf = MySQLConf.select().order_by(MySQLConf.id).first()  # type: MySQLConf
    else:
        conf = MySQLConf.get(name=conf_name)  # type: MySQLConf

    image = get_mysql_image()
    temp_name = get_id()
    client.containers.run(
        image, name=temp_name,
        command='bash',
        remove=True,
        volumes={
            volume.name: {'bind': '/etc/mysql/conf.d/', 'mode': 'rw'}
        },
        detach=True, stdout=True, stderr=True, tty=True
    )
    container = get_container_by_name(temp_name)
    cnf_file_name = '{}.cnf'.format(conf.name)
    with NamedTemporaryFile(buffering=0, suffix='.cnf') as cnf_file:
        cnf_file.write(conf.content.encode('utf8'))
        send_file(container, cnf_file.name, cnf_file_name, '/etc/mysql/conf.d/')
    container.exec_run(
        "bash -c '{}'".format(
            "chmod 644 /etc/mysql/conf.d/{0} && "
            "chown root:root /etc/mysql/conf.d/{0}".format(cnf_file_name)
        )
    )
    container.stop()
    return volume


def copy_volume(from_volume: Volume, to_volume: Volume):
    image = get_mysql_image()
    temp_name = get_id()
    c = client.containers.run(
        image, name=temp_name,
        command='bash -c "rm -rf /data/to/* && cp -a /data/from/* /data/to/"',
        remove=True,
        volumes={
            from_volume.name: {'bind': '/data/from', 'mode': 'rw'},
            to_volume.name: {'bind': '/data/to', 'mode': 'rw'}
        },
        detach=True
    )  # type: Container
    c.wait(condition='removed')


def clean_volume(volume: Volume):
    image = get_mysql_image()
    temp_name = get_id()
    c = client.containers.run(
        image, name=temp_name,
        command='bash -c "rm -rf /data/*"',
        remove=True,
        volumes={
            volume.name: {'bind': '/data', 'mode': 'rw'},
        },
        detach=True
    )  # type: Container
    c.wait(condition='removed')


def init_container(db_info: DBInfo) -> Container:
    if is_port_in_use(db_info.port):
        raise Exception('the port {} is in use.'.format(db_info.port))

    image = get_mysql_image()

    container = client.containers.run(
        image, name=f'myvc.{db_info.id}',
        volumes={
            db_info.conf_volume: {'bind': '/etc/mysql/conf.d', 'mode': 'rw'},
            db_info.current_version.volume: {'bind': '/var/lib/mysql', 'mode': 'rw'},
        },
        ports={'3306/tcp': db_info.port},
        environment={'MYSQL_ROOT_PASSWORD': db_info.password},
        detach=True,
    )
    return container


def new_db(name: str, port: int, password: str):
    with DB.atomic():
        db_info = DBInfo(
            name=name, port=port, password=password
        )
        conf_volume = init_mysql_conf_volume()
        db_info.conf_volume = conf_volume.name
        db_info.save()

        data_volume = client.volumes.create(get_id())
        data_version = DataVersion()
        data_version.db = db_info
        data_version.volume = data_volume.name
        data_version.name = 'Init {}'.format(name)
        data_version.save()
        db_info.current_version = data_version
        db_info.save()

        try:
            container = init_container(db_info)
            db_info.container_id = container.id
            db_info.save()
            return db_info.id
        except Exception:
            conf_volume.remove()
            data_volume.remove()
            raise


def rm_db(db_id: int):
    with DB.atomic():
        db_info = DBInfo.get_or_none(id=db_id)
        stop_db(db_id)
        if db_info:
            for v in db_info.versions:
                rm_volume_by_name(v.volume)
                v.delete_instance()
            rm_volume_by_name(db_info.conf_volume)
        db_info.delete_instance()


def rm_version(db_id: int, version_id: int):
    db_info = DBInfo.get(id=db_id)
    if db_info.current_version and version_id == db_info.current_version.id:
        raise Exception("Can't rm using version")
    version = DataVersion.get(db=db_id, id=version_id)  # type: DataVersion
    if not version.parent:
        raise Exception("Can't rm root version")
    if db_info.current_version and f'/{version.id}/' in db_info.current_version.path:
        raise Exception("The using version:{} is {}'s child".format(db_info.current_version.name, version.name))
    if version.child_versions.exists():
        answer = questionary.confirm(
            'version [{}({})] has children\n\n{}\n\nwill delete all these versions, please confirm.'.format(
                version.volume, version.name, version.children_tree
            )
        ).ask()
        if not answer:
            return

    with DB.atomic():
        for v in version.self_and_child_versions:
            rm_volume_by_name(v.volume)
            v.delete_instance()


def clean_data(db_id: int, version_id: int = None):
    db_info = DBInfo.get(id=db_id)
    if not version_id and not db_info.current_version:
        raise Exception("{} don't have using version".format(db_info.name))
    if version_id:
        version = DataVersion.get(id=version_id, db=db_info)  # type: DataVersion
    else:
        version = db_info.current_version
    is_clean_current_version = version == db_info.current_version
    volume = get_volume_by_name(version.volume)
    assert volume, "version {} not exists".format(volume.name)
    if is_clean_current_version:
        stop_db(db_id)
    clean_volume(volume)
    if is_clean_current_version:
        start_db(db_id)


def stop_db(db_id: int):
    db_info = DBInfo.get_or_none(id=db_id)
    if db_info and db_info.container_id:
        try:
            container = client.containers.get(db_info.container_id)  # type: Container
            container.stop()
            container.wait()
            container.remove()
            db_info.container_id = None
            db_info.save()
        except NotFound:
            pass
    possible_container = get_container_by_name(f'myvc.{db_id}')
    if possible_container:
        possible_container.kill()
        possible_container.wait()
        possible_container.remove()
        if db_info:
            db_info.container_id = None
            db_info.save()


def start_db(db_id: int):
    db_info = DBInfo.get(id=db_id)
    current_data_volume = get_volume_by_name(db_info.current_version.volume)
    if not current_data_volume:
        raise Exception("{}'s current data version {} not exists".format(db_info.name, db_info.current_version.name))
    conf_volume = get_volume_by_name(db_info.conf_volume)
    if not conf_volume:
        raise Exception("{}'s conf volume not exists".format(db_info.name))
    stop_db(db_id)
    container = init_container(db_info)
    db_info.container_id = container.id
    db_info.save()


def apply_version(db_id: int, version_id: int):
    db_info = DBInfo.get(id=db_id)  # type: DBInfo
    version = DataVersion.get(db=db_info, id=version_id)  # type: DataVersion
    stop_db(db_id)
    db_info.current_version = version
    container = init_container(db_info)
    db_info.container_id = container.id
    db_info.save()


def copy_from(db_id: int, from_version_id: int):
    db_info = DBInfo.get(id=db_id)  # type: DBInfo
    from_version = DataVersion.get(db=db_info, id=from_version_id)  # type: DataVersion
    assert db_info.current_version, "{}'s using version not exists".format(db_info.name)
    current_volume = get_volume_by_name(db_info.current_version.volume)
    assert current_volume, "{}'s using version {} not exists".format(db_info.name, db_info.current_version.name)
    from_volume = get_volume_by_name(from_version.volume)
    assert from_volume, "volume {} not exists".format(from_volume.name)
    stop_db(db_id)
    copy_volume(from_volume, current_volume)
    start_db(db_id)


def apply_sql(db_id: int, sql_path, database_name: str = None):
    sql_path = os.path.expanduser(sql_path)
    if not os.path.exists(sql_path):
        raise Exception('{} not exists'.format(sql_path))
    sql_path = os.path.abspath(sql_path)
    db_info, container = check_is_running(db_id)
    if sql_path.endswith('.gz'):
        try:
            sql_file_content = gzip.GzipFile(sql_path).read()
            with NamedTemporaryFile(buffering=0, suffix='.sql') as sql_file:
                sql_file.write(sql_file_content)
                sql_file_name = os.path.basename(sql_file.name)
                send_file(container, sql_file.name, sql_file_name, '/')
        except Exception as e:
            questionary.print('parse sql file failed -> {}'.format(e))
            exit(0)
    else:
        sql_file_name = os.path.basename(sql_path)
        send_file(container, sql_path, sql_file_name, '/')
    if database_name:
        print(container.exec_run(
            "bash -c 'exec mysql -u root -p{} -D {} < \"/{}\"'".format(
                db_info.password, database_name, sql_file_name
            )
        ).output.decode())
    else:
        print(container.exec_run(
            "bash -c 'exec mysql -u root -p{} < \"/{}\"'".format(db_info.password, sql_file_name)
        ).output.decode())


def backup_version(db_id: int, name: str, version_id: int = None) -> Volume:
    db_info = DBInfo.get(id=db_id)
    if version_id:
        version = DataVersion.get(db=db_info, id=version_id)
    else:
        version = db_info.current_version
        assert version, "Can't find {}'s current version".format(db_info.name)

    volume = get_volume_by_name(version.volume)
    assert volume, "Can't find volume: {}".format(version.volume)

    if version == db_info.current_version:
        stop_db(db_id)

    new_volume = client.volumes.create(get_id())
    new_version = DataVersion(
        volume=new_volume.name,
        name=name,
        parent=version,
        db=db_info
    )
    copy_volume(volume, new_volume)
    new_version.save()

    if version == db_info.current_version:
        start_db(db_id)

    return new_version


def db_shell(db_id):
    db_info, container = check_is_running(db_id)
    os.system(
        "docker exec -it {} bash -c 'mysql -u root -p{}'".format(
            db_info.container_id, db_info.password
        )
    )

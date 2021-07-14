#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/8 11:30
import json
from myvc.data_version import DataVersion
from myvc.utils import get_id


class DBInfo:

    def __init__(self):
        self.id = get_id()
        self.name = None
        self.password = None
        self.version = None  # type: DataVersion
        self.current_version = None
        self.conf_volume = None
        self.port = None
        self.container_id = None
        self.create_at = None
        self.start_at = None
        self.stop_at = None

    def to_json(self):
        return json.dumps({
            'id': self.id,
            'name': self.name,
            'password': self.password,
            'version': (self.version and self.version.to_json()) or self.version,
            'current_version': self.current_version,
            'conf_volume': self.conf_volume,
            'port': self.port,
            'container_id': self.container_id,
            'create_at': self.create_at,
            'start_at': self.start_at,
            'stop_at': self.stop_at
        })

    @classmethod
    def load_from_json(cls, json_string):
        # type: (str) -> DBInfo
        _dict = json.loads(json_string)
        db_info = DBInfo()
        db_info.id = _dict['id']
        db_info.name = _dict['name']
        db_info.password = _dict['password']
        db_info.version = _dict['version'] and DataVersion.load_from_json(_dict['version']) or None
        db_info.current_version = _dict['current_version']
        db_info.conf_volume = _dict['conf_volume']
        db_info.port = _dict['port']
        db_info.container_id = _dict['container_id']
        db_info.create_at = _dict['create_at']
        db_info.start_at = _dict['start_at']
        db_info.stop_at = _dict['stop_at']
        return db_info

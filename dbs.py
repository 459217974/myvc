#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/11 13:09
import json
import os
from typing import List

from db_info import DBInfo


class DBs:

    def __init__(self):
        self.dbs = []  # type: List[DBInfo]

    def get_db_info_by_id(self, db_id):
        _ = list(
            filter(
                lambda db: db.id == db_id,
                self.dbs
            )
        )
        return _[0] if _ else None

    def delete_db_info_by_id(self, db_id):
        for i, db in enumerate(self.dbs):
            if db.id == db_id:
                self.dbs.pop(i)
                break

    def save(self):
        _ = []
        for db_info in self.dbs:
            _.append(db_info.to_json())
        path = os.path.join(os.path.dirname(__file__), 'dbs')
        with open(path, 'w') as f:
            json.dump(_, f)

    @classmethod
    def load(cls):
        # type: () -> DBs
        dbs = DBs()

        path = os.path.join(os.path.dirname(__file__), 'dbs')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                _dict = json.load(f)
            for db_info in _dict:
                dbs.dbs.append(DBInfo.load_from_json(db_info))

        return dbs

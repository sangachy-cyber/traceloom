# -*- coding: utf-8 -*-
"""任务存储模块。

使用 SQLite 数据库存储织径任务的状态和信息。
"""

import sqlite3
from datetime import datetime, timezone

from traceloom.app.api.v1.schemas import WeaveRequest


class TaskStore:
    """任务存储类，使用 SQLite 数据库。

    示例:
        from traceloom.storage.task_store import TaskStore
        from traceloom.app.api.v1.schemas import WeaveRequest

        # 创建任务存储实例
        task_store = TaskStore()

        # 创建任务
        task_id = "task_123"
        request = WeaveRequest(...)
        engine_name = "reweave"
        task_store.create_task(task_id, request, engine_name)

        # 更新任务状态
        task_store.update_status(task_id, "running")

        # 任务失败
        task_store.update_status(task_id, "failed", error="执行失败")
    """

    def __init__(self, db_path: str = "weaver_tasks.db"):
        """初始化任务存储。

        参数:
            db_path: SQLite 数据库文件路径
        """

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构。"""

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            target_ip TEXT,
            weaving_pattern TEXT,
            engine TEXT,
            host TEXT,
            port INTEGER,
            engine_id INTEGER,
            path_name TEXT,
            status TEXT,
            error TEXT,
            playback_file_path TEXT,
            started_at TEXT,
            created_at TEXT,
            updated_at TEXT
        )""")
        self.conn.commit()

    def create_task(self, task_id: str, req: WeaveRequest, engine_name: str):
        """创建新任务。

        参数:
            task_id: 任务唯一标识
            req: 编织请求对象
            engine_name: 编织引擎名称
        """

        dev = req.impairment_device
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'accepted', NULL, NULL, NULL, ?, ?)",
            (
                task_id,
                req.target_ip,
                req.weaving_pattern,
                engine_name,
                dev.host,
                dev.port,
                dev.engine_id,
                dev.path_name,
                now,
                now,
            ),
        )
        self.conn.commit()

    def update_playback_file(self, task_id: str, playback_file_path: str):
        """更新任务的回放文件路径。

        参数:
            task_id: 任务唯一标识
            playback_file_path: 回放文件路径
        """

        self.conn.execute(
            "UPDATE tasks SET playback_file_path=?, updated_at=? WHERE task_id=?",
            (playback_file_path, datetime.now(timezone.utc).isoformat(), task_id),
        )
        self.conn.commit()

    def update_started_at(self, task_id: str):
        """更新任务的开始时间。

        参数:
            task_id: 任务唯一标识
        """

        self.conn.execute(
            "UPDATE tasks SET started_at=?, updated_at=? WHERE task_id=?",
            (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), task_id),
        )
        self.conn.commit()

    def update_status(self, task_id: str, status: str, error: str = None):
        """更新任务状态。

        参数:
            task_id: 任务唯一标识
            status: 任务状态
            error: 错误信息（可选）
        """

        self.conn.execute(
            "UPDATE tasks SET status=?, error=?, updated_at=? WHERE task_id=?",
            (status, error, datetime.now(timezone.utc).isoformat(), task_id),
        )
        self.conn.commit()

    def get_task(self, task_id: str):
        """获取任务信息。

        参数:
            task_id: 任务唯一标识

        返回:
            dict: 任务信息字典
        """

        cursor = self.conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "task_id": row[0],
            "target_ip": row[1],
            "weaving_pattern": row[2],
            "engine": row[3],
            "host": row[4],
            "port": row[5],
            "engine_id": row[6],
            "path_name": row[7],
            "status": row[8],
            "error": row[9],
            "playback_file_path": row[10],
            "started_at": row[11],
            "created_at": row[12],
            "updated_at": row[13],
        }

    def get_all_tasks(self):
        """获取所有任务。

        返回:
            list: 任务信息字典列表
        """

        cursor = self.conn.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()

        tasks = []
        for row in rows:
            tasks.append(
                {
                    "task_id": row[0],
                    "target_ip": row[1],
                    "weaving_pattern": row[2],
                    "engine": row[3],
                    "host": row[4],
                    "port": row[5],
                    "engine_id": row[6],
                    "path_name": row[7],
                    "status": row[8],
                    "playback_file_path": row[10],
                    "started_at": row[11],
                    "error": row[9],
                    "created_at": row[12],
                    "updated_at": row[13],
                }
            )

        return tasks

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试核心配置功能"""

from pathlib import Path

from traceloom.core.config import settings


def test_db_path():
    """测试数据库路径和目录创建功能"""
    # 验证数据库目录路径配置
    assert isinstance(settings.DB_DIR, Path)
    assert "db" in str(settings.DB_DIR)

    # 测试目录创建
    settings.DB_DIR.mkdir(parents=True, exist_ok=True)

    # 验证目录是否存在
    assert settings.DB_DIR.exists(), "数据库目录不存在"
    assert settings.DB_DIR.is_dir(), "数据库路径不是目录"

    # 验证目录权限
    assert settings.DB_DIR.stat().st_mode & 0o777 >= 0o700, "数据库目录权限不正确"

    # 验证数据库文件路径
    db_file = settings.DB_DIR / "weaver_tasks.db"
    assert isinstance(db_file, Path)
    assert db_file.parent == settings.DB_DIR


def test_output_dirs():
    """测试输出目录配置"""
    # 验证各种输出目录配置
    assert isinstance(settings.OUTPUT_DIR, Path)
    assert isinstance(settings.AFTER_LABEL_DIR, Path)

    # 测试目录创建
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings.AFTER_LABEL_DIR.mkdir(parents=True, exist_ok=True)

    # 验证目录是否存在
    assert settings.OUTPUT_DIR.exists(), "输出目录不存在"
    assert settings.AFTER_LABEL_DIR.exists(), "标签后目录不存在"

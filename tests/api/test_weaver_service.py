# -*- coding: utf-8 -*-
"""测试 Weaver Service API 端点"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from pathlib import Path

from traceloom.app import create_app
from traceloom.services.weaver_service import WeaverService
from traceloom.storage.task_store import TaskStore

# 创建测试客户端
client = TestClient(create_app())


@pytest.fixture
def mock_task_store():
    """模拟任务存储"""
    with patch("traceloom.app.api.v1.endpoints.task_store") as mock:
        # 模拟创建任务
        mock.create_task.return_value = None
        # 模拟更新任务状态
        mock.update_status.return_value = None
        # 模拟更新回放文件路径
        mock.update_playback_file.return_value = None
        # 模拟更新开始时间
        mock.update_started_at.return_value = None

        # 模拟获取任务
        def mock_get_task(task_id):
            if task_id == "non_existent_task":
                return None
            return {
                "task_id": task_id,
                "target_ip": "10.10.10.10",
                "weaving_pattern": "s0x2 -> s9x1",
                "engine": "reweaver",
                "host": "160.100.15.195",
                "port": 8080,
                "engine_id": 1,
                "path_name": "MyLink",
                "status": "running",
                "error": None,
                "playback_file_path": f"/tmp/playback/{task_id}.txt",
                "started_at": "2026-01-28T10:00:00Z",
                "created_at": "2026-01-28T09:59:00Z",
                "updated_at": "2026-01-28T10:00:00Z",
            }

        mock.get_task.side_effect = mock_get_task
        yield mock


@pytest.fixture
def mock_weaver_service():
    """模拟编织服务"""
    with patch("traceloom.app.api.v1.endpoints.weaver_service") as mock:
        # 模拟执行任务
        mock.execute_task.return_value = None
        mock.execute_reweave.return_value = None
        mock.execute_stitch.return_value = None
        mock.execute_dream.return_value = None
        # 模拟取消任务
        mock.cancel_task.return_value = None

        # 模拟获取回放文件路径
        def mock_get_playback_file_path(task_id):
            return f"/tmp/playback/{task_id}.txt"

        mock.get_playback_file_path.side_effect = mock_get_playback_file_path
        # 模拟清理过期文件
        mock.cleanup_expired_files.return_value = None
        yield mock


@pytest.fixture
def mock_path_exists():
    """模拟文件存在"""
    with patch("pathlib.Path.exists") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def sample_weave_request():
    """示例编织请求"""
    return {
        "target_ip": "10.10.10.10",
        "weaving_pattern": "s0x2 -> s9x1",
        "impairment_device": {"host": "160.100.15.195", "port": 8080, "engine_id": 1, "path_name": "MyLink"},
    }


# 测试健康检查端点
def test_health_check():
    """测试健康检查端点"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# 测试自动选择引擎端点
def test_weave_endpoint(mock_task_store, mock_weaver_service, sample_weave_request):
    """测试自动选择引擎端点"""
    # 测试 POST /api/v1/weave
    response = client.post("/api/v1/weave", json=sample_weave_request)
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert "engine" in response.json()
    assert "status" in response.json()
    assert "message" in response.json()
    assert "download_url" in response.json()

    # 测试 GET /api/v1/weave/{task_id}
    task_id = "weave_test_123"
    response = client.get(f"/api/v1/weave/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id

    # 测试 DELETE /api/v1/weave/{task_id}
    response = client.delete(f"/api/v1/weave/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["status"] == "completed"

    # 测试 GET /api/v1/weave/{task_id}/playback
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("traceloom.app.api.v1.endpoints.FileResponse") as mock_file_response,
    ):
        from fastapi import Response

        mock_exists.return_value = True
        mock_file_response.return_value = Response(status_code=200)
        response = client.get(f"/api/v1/weave/{task_id}/playback")
        assert response.status_code == 200


# 测试 Reweaver 端点
def test_reweave_endpoint(mock_task_store, mock_weaver_service, sample_weave_request):
    """测试 Reweaver 端点"""
    # 测试 POST /api/v1/reweave
    response = client.post("/api/v1/reweave", json=sample_weave_request)
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert "engine" in response.json()
    assert "status" in response.json()
    assert "message" in response.json()
    assert "download_url" in response.json()

    # 测试 GET /api/v1/reweave/{task_id}
    task_id = "reweave_test_123"
    response = client.get(f"/api/v1/reweave/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id

    # 测试 DELETE /api/v1/reweave/{task_id}
    response = client.delete(f"/api/v1/reweave/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["status"] == "completed"

    # 测试 GET /api/v1/reweave/{task_id}/playback
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("traceloom.app.api.v1.endpoints.FileResponse") as mock_file_response,
    ):
        from fastapi import Response

        mock_exists.return_value = True
        mock_file_response.return_value = Response(status_code=200)
        response = client.get(f"/api/v1/reweave/{task_id}/playback")
        assert response.status_code == 200


# 测试 Stitcher 端点
def test_stitch_endpoint(mock_task_store, mock_weaver_service, sample_weave_request):
    """测试 Stitcher 端点"""
    # 测试 POST /api/v1/stitch
    response = client.post("/api/v1/stitch", json=sample_weave_request)
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert "engine" in response.json()
    assert "status" in response.json()
    assert "message" in response.json()
    assert "download_url" in response.json()

    # 测试 GET /api/v1/stitch/{task_id}
    task_id = "stitch_test_123"
    response = client.get(f"/api/v1/stitch/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id

    # 测试 DELETE /api/v1/stitch/{task_id}
    response = client.delete(f"/api/v1/stitch/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["status"] == "completed"

    # 测试 GET /api/v1/stitch/{task_id}/playback
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("traceloom.app.api.v1.endpoints.FileResponse") as mock_file_response,
    ):
        from fastapi import Response

        mock_exists.return_value = True
        mock_file_response.return_value = Response(status_code=200)
        response = client.get(f"/api/v1/stitch/{task_id}/playback")
        assert response.status_code == 200


# 测试 Dreamer 端点
def test_dream_endpoint(mock_task_store, mock_weaver_service, sample_weave_request):
    """测试 Dreamer 端点"""
    # 测试 POST /api/v1/dream
    response = client.post("/api/v1/dream", json=sample_weave_request)
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert "engine" in response.json()
    assert "status" in response.json()
    assert "message" in response.json()
    assert "download_url" in response.json()

    # 测试 GET /api/v1/dream/{task_id}
    task_id = "dream_test_123"
    response = client.get(f"/api/v1/dream/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id

    # 测试 DELETE /api/v1/dream/{task_id}
    response = client.delete(f"/api/v1/dream/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["status"] == "completed"

    # 测试 GET /api/v1/dream/{task_id}/playback
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("traceloom.app.api.v1.endpoints.FileResponse") as mock_file_response,
    ):
        from fastapi import Response

        mock_exists.return_value = True
        mock_file_response.return_value = Response(status_code=200)
        response = client.get(f"/api/v1/dream/{task_id}/playback")
        assert response.status_code == 200


# 测试错误处理
def test_error_handling(mock_task_store, sample_weave_request):
    """测试错误处理"""
    # 测试任务不存在
    mock_task_store.get_task.return_value = None
    task_id = "non_existent_task"
    response = client.get(f"/api/v1/weave/{task_id}")
    assert response.status_code == 404
    assert "detail" in response.json()

    # 测试回放文件不存在
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        response = client.get(f"/api/v1/weave/{task_id}/playback")
        assert response.status_code == 404
        assert "detail" in response.json()

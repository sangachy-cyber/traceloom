#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HoloWAN交互示例脚本

展示如何使用重构后的HoloWANManager类执行完整的HoloWAN交互流程。
"""

from traceloom.io.holowan import HoloWANManager


def main():
    """主函数"""
    # 引擎ID（根据实际情况调整）
    engine_id = 1

    # 目标IP地址
    target_ip = "10.10.10.10"

    # 路径名称
    path_name = "LoomNet"

    # 回放文件路径
    playback_file_path = "../output/holowan/sim_task_20260122_103424_udw81q.txt"

    # 获取回放文件名称
    playback_name = playback_file_path.split("/")[-1]

    # 初始化HoloWAN管理器
    holowan_manager = HoloWANManager(engine_id=engine_id)

    try:
        # 1. 设置分类规则
        print("\n1. 设置分类规则...")
        if holowan_manager.setup_rules(path_name, target_ip):
            print("✅ 分类规则设置成功")
        else:
            print("❌ 分类规则设置失败")
            return

        # 2. 应用回放文件
        print("\n2. 应用回放文件...")
        if holowan_manager.apply_playback(playback_file_path):
            print("✅ 回放文件应用成功")
        else:
            print("❌ 回放文件应用失败")
            return

        # 3. 这里可以添加业务逻辑，比如进行网络测试等
        print("\n3. 执行业务逻辑...")
        # TODO: 添加您的业务逻辑

        # 4. 清理资源
        print("\n4. 清理资源...")
        if holowan_manager.cleanup(target_ip, playback_name):
            print("✅ 资源清理成功")
        else:
            print("❌ 资源清理失败")
            return

        print("\n🎉 完整流程执行成功！")

    except Exception as e:
        print(f"\n❌ 执行过程中发生错误: {e}")
        # 确保资源被清理
        holowan_manager.cleanup(target_ip, playback_name)


if __name__ == "__main__":
    main()

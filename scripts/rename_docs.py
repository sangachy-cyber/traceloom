#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名参考文档，将LoomNet替换为TraceLoom
"""

from pathlib import Path


def rename_reference_docs(directory: str):
    """重命名参考文档，将LoomNet替换为TraceLoom

    Args:
        directory: 要处理的目录路径
    """
    # 遍历目录下所有包含LoomNet的markdown文件
    for file_path in Path(directory).glob("LoomNet*.md"):
        print(f"处理文件: {file_path}")

        try:
            # 生成新文件名
            new_filename = file_path.name.replace("LoomNet", "TraceLoom")
            new_file_path = file_path.parent / new_filename

            # 读取旧文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 更新内容中的LoomNet为TraceLoom
            updated_content = content.replace('LoomNet', 'TraceLoom')

            # 写入新文件
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            # 删除旧文件
            file_path.unlink()

            print(f"✓ 重命名完成: {file_path} → {new_file_path}")
        except Exception as e:
            print(f"✗ 处理失败: {file_path}, 错误: {e}")


if __name__ == '__main__':
    # 更新reference目录下的所有文档
    reference_dir = Path(__file__).parent.parent / 'docs' / 'reference'
    rename_reference_docs(reference_dir)
    print("\n所有参考文档更新完成！")

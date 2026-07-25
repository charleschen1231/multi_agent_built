#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Agent System Builder - Web UI 启动入口

基于 Gradio 的 Web 界面，提供：
- 数据管理中心
- JSON 配置上传与校验
- 执行流程可视化
- SFT/DPO/GRPO 训练管理
"""

import os
import sys
import argparse
import subprocess


def check_and_install_dependencies():
    """检查并安装依赖"""
    required_packages = [
        'gradio>=4.0.0',
        'sqlalchemy>=2.0.0',
        'pydantic>=2.0.0',
        'networkx>=3.0',
        'jinja2>=3.1.2',
        'PyYAML>=6.0',
        'httpx>=0.24.0',
        'openai>=1.0.0',
        'numpy>=1.26.0'
    ]
    
    optional_packages = {
        'ms-swift': 'ms-swift>=2.0.0',
        'verl': 'verl>=0.1.0'
    }
    
    print("检查依赖...")
    
    for package in required_packages:
        package_name = package.split('>=')[0]
        try:
            __import__(package_name.replace('-', '_'))
        except ImportError:
            print(f"安装 {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    
    # 检查可选依赖
    for name, package in optional_packages.items():
        try:
            if name == 'ms-swift':
                import swift
            elif name == 'verl':
                import verl
            print(f"✅ {name} 已安装")
        except ImportError:
            print(f"⚠️ {name} 未安装，训练功能将使用命令行方式")
            print(f"   如需安装，请运行: pip install {package}")
    
    print("依赖检查完成！")


def init_database():
    """初始化数据库"""
    from database.db_manager import DatabaseManager
    
    print("初始化数据库...")
    db = DatabaseManager()
    print(f"✅ 数据库已初始化: {db.db_path}")
    return db


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Multi-Agent System Builder - Web UI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认启动
  python main_web.py
  
  # 指定端口
  python main_web.py --port 8080
  
  # 允许外部访问
  python main_web.py --host 0.0.0.0 --port 7860
  
  # 创建公开链接
  python main_web.py --share
        """
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='服务器主机地址 (默认: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=7860,
        help='服务器端口 (默认: 7860)'
    )
    
    parser.add_argument(
        '--share',
        action='store_true',
        help='创建公开访问链接 (Gradio Tunnel)'
    )
    
    parser.add_argument(
        '--no-install',
        action='store_true',
        help='跳过依赖检查和安装'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    args = parser.parse_args()
    
    # 检查依赖
    if not args.no_install:
        check_and_install_dependencies()
    
    # 初始化数据库
    init_database()
    
    # 导入并启动应用
    print("启动 Web UI...")
    from web.app import launch_app
    
    try:
        launch_app(
            server_name=args.host,
            server_port=args.port,
            share=args.share
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
        sys.exit(0)
    except Exception as e:
        print(f"启动失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

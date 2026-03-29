# -*- coding: utf-8 -*-
"""
自动化测试运行器

使用方法:
    python tests/run_tests.py              # 运行所有测试
    python tests/run_tests.py --manager     # 只运行管理器测试
    python tests/run_tests.py --integration # 只运行集成测试
    python tests/run_tests.py --report     # 生成HTML报告
"""

import sys
import os
import argparse
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests(test_path=None, markers=None, report=False, verbose=True):
    """运行测试"""
    cmd = [sys.executable, '-m', 'pytest', 'tests/ui/']

    if test_path:
        cmd = [sys.executable, '-m', 'pytest', test_path]

    if markers:
        cmd.extend(['-m', markers])

    if verbose:
        cmd.append('-v')

    if report:
        cmd.extend(['--html=tests/ui_report.html', '--self-contained-html'])

    cmd.extend(['--tb=short', '-x'])  # 遇到第一个失败就停止

    print(f"运行命令: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return result.returncode


def check_environment():
    """检查测试环境"""
    print("检查测试环境...")
    print("=" * 60)

    checks = []

    try:
        import pytest
        checks.append(("pytest", True))
    except ImportError:
        checks.append(("pytest", False))

    try:
        import pandas
        checks.append(("pandas", True))
    except ImportError:
        checks.append(("pandas", False))

    try:
        from data_source.db.connection import get_engine
        engine = get_engine()
        checks.append(("MySQL", True))
    except Exception as e:
        checks.append(("MySQL", False))
        print(f"MySQL 连接失败: {e}")

    try:
        from data_source.cache import get_cache
        cache = get_cache()
        if cache.is_available():
            checks.append(("Redis", True))
        else:
            checks.append(("Redis", False))
    except Exception as e:
        checks.append(("Redis", False))
        print(f"Redis 连接失败: {e}")

    print("\n环境检查结果:")
    for name, status in checks:
        status_str = "✓" if status else "✗"
        print(f"  {status_str} {name}")

    all_passed = all(status for _, status in checks)
    return all_passed


def main():
    parser = argparse.ArgumentParser(description='自动化测试运行器')
    parser.add_argument('--manager', action='store_true', help='只运行管理器测试')
    parser.add_argument('--integration', action='store_true', help='只运行集成测试')
    parser.add_argument('--report', action='store_true', help='生成HTML报告')
    parser.add_argument('--check', action='store_true', help='只检查环境')
    parser.add_argument('--verbose', '-v', action='store_true', default=True)

    args = parser.parse_args()

    if args.check:
        check_environment()
        return

    if not check_environment():
        print("\n⚠ 环境检查未通过，请先修复环境问题")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("开始运行测试")
    print("=" * 60)

    if args.manager:
        exit_code = run_tests('tests/ui/test_managers.py', report=args.report)
    elif args.integration:
        exit_code = run_tests('tests/ui/test_integration.py', report=args.report)
    else:
        exit_code = run_tests(report=args.report)

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()

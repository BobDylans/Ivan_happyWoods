"""依赖自检脚本
运行: python scripts/verify_deps.py [--json] [--show-optional] [--fail-fast]
用于快速检测核心依赖是否已安装，便于环境巡检。
"""
from __future__ import annotations
import json
import sys
import argparse
from dataclasses import dataclass
from importlib.util import find_spec
from typing import List, Iterable, Dict

@dataclass(frozen=True)
class Package:
    name: str               # 安装名称 (pip 名称)
    import_name: str        # 实际 import 名称 (模块顶级包)
    required: bool = True   # 是否为必要依赖
    category: str = "core"  # 分类标签

    def is_installed(self) -> bool:
        return find_spec(self.import_name) is not None

# 定义依赖集合（向后迁移时只需在此列表新增）
PACKAGES: List[Package] = [
    # 必要依赖
    Package("fastapi", "fastapi"),
    Package("uvicorn", "uvicorn"),
    Package("pydantic", "pydantic"),
    Package("pydantic-settings", "pydantic_settings"),
    Package("langgraph", "langgraph"),
    Package("langgraph-checkpoint", "langgraph.checkpoint"),
    Package("langchain", "langchain"),
    Package("httpx", "httpx"),
    Package("websockets", "websockets"),
    Package("sqlalchemy", "sqlalchemy"),
    Package("asyncpg", "asyncpg"),
    Package("alembic", "alembic"),
    Package("psycopg2-binary", "psycopg2"),
    Package("pytest", "pytest"),
    Package("qdrant-client", "qdrant_client"),
    Package("pypdf", "pypdf"),
    # 可选依赖
    Package("python-dotenv", "dotenv", required=False, category="optional"),
    Package("pydub", "pydub", required=False, category="optional"),
    Package("email-validator", "email_validator", required=False, category="optional"),
    Package("passlib", "passlib", required=False, category="optional"),
]


def group_packages(packages: Iterable[Package]) -> Dict[str, List[Package]]:
    grouped: Dict[str, List[Package]] = {}
    for p in packages:
        grouped.setdefault(p.category, []).append(p)
    return grouped


def build_report() -> Dict[str, Dict[str, List[str]]]:
    required = [p for p in PACKAGES if p.required]
    optional = [p for p in PACKAGES if not p.required]
    return {
        "required": {
            "installed": [p.name for p in required if p.is_installed()],
            "missing": [p.name for p in required if not p.is_installed()],
        },
        "optional": {
            "installed": [p.name for p in optional if p.is_installed()],
            "missing": [p.name for p in optional if not p.is_installed()],
        },
    }


def print_human(report: Dict[str, Dict[str, List[str]]], show_optional: bool) -> None:
    print("[依赖检测] 开始执行脚本...\n")
    print("=== 必要依赖 (Required) ===")
    for name in report["required"]["installed"]:
        print(f"[OK] {name}")
    for name in report["required"]["missing"]:
        print(f"[MISS] {name}")

    if show_optional:
        print("\n=== 可选依赖 (Optional) ===")
        for name in report["optional"]["installed"]:
            print(f"[OK] {name}")
        for name in report["optional"]["missing"]:
            print(f"[MISS] {name}")

    if report["required"]["missing"]:
        print("\n安装缺失必要依赖示例:")
        print("pip install " + " ".join(report["required"]["missing"]))
    if show_optional and report["optional"]["missing"]:
        print("\n可选依赖安装示例:")
        print("pip install " + " ".join(report["optional"]["missing"]))

    print("\n提示: 可统一执行 -> pip install -r requirements.txt")
    print("建议: 安装后运行 -> mypy src/ | pytest")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="依赖检测脚本")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    parser.add_argument("--show-optional", action="store_true", help="显示可选依赖检测结果")
    parser.add_argument("--fail-fast", action="store_true", help="若存在缺失必要依赖以非零状态码退出")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report()

    if args.json:
        # JSON 输出包含分类，方便 CI 集成
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human(report, show_optional=args.show_optional)

    if args.fail_fast and report["required"]["missing"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

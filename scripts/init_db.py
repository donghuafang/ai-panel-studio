#!/usr/bin/env python3
"""AI Panel Studio — 数据库初始化脚本

用法：
    cd backend
    python ../scripts/init_db.py               # 创建所有表
    python ../scripts/init_db.py --drop         # 删除后重建
    python ../scripts/init_db.py --seed         # 创建表 + 导入样例数据

依赖：需从 backend/ 目录或项目根目录运行，确保 app 模块可导入。
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 将 backend/ 加入 Python Path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(str(BACKEND_DIR))

from app.database import engine, Base, SessionLocal
from app.models import Discussion, Guest, Speech, Consensus, Divergence


def create_tables():
    """创建所有数据库表（幂等操作，已存在的表不重复创建）。"""
    Base.metadata.create_all(bind=engine)
    print("✅ 所有数据库表已创建 (5 tables)")

    # 打印创建的表名
    table_names = Base.metadata.tables.keys()
    for name in sorted(table_names):
        print(f"   └─ {name}")
    return True


def drop_tables():
    """删除所有数据库表。"""
    confirm = input("⚠️  确认删除所有表？数据将不可恢复 [y/N]: ")
    if confirm.lower() != "y":
        print("已取消。")
        return False

    Base.metadata.drop_all(bind=engine)
    print("✅ 所有数据库表已删除")
    return True


def verify_tables():
    """验证表结构是否正确创建。"""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected = {"discussions", "guests", "speeches", "consensus", "divergence"}
    actual = set(tables)

    print(f"\n📋 表结构验证:")
    print(f"   期望: {sorted(expected)}")
    print(f"   实际: {sorted(actual)}")

    if expected.issubset(actual):
        print("✅ 表结构验证通过")

        # 打印每个表的列信息
        for table in sorted(expected):
            columns = inspector.get_columns(table)
            col_names = [c["name"] for c in columns]
            print(f"   └─ {table}: {', '.join(col_names)}")

        # 打印索引信息
        print("\n📋 索引验证:")
        for table in sorted(expected):
            indexes = inspector.get_indexes(table)
            for idx in indexes:
                print(f"   └─ {table}.{idx['name']}: {idx['column_names']}")

        return True
    else:
        missing = expected - actual
        print(f"❌ 缺少表: {missing}")
        return False


def import_seed_data():
    """导入样例数据。"""
    seed_path = BACKEND_DIR.parent / "scripts" / "seed_data.py"
    if not seed_path.exists():
        print(f"❌ 未找到种子数据文件: {seed_path}")
        return False

    print(f"📥 导入种子数据: {seed_path}")
    # 动态导入 seed_data 模块
    import importlib.util

    spec = importlib.util.spec_from_file_location("seed_data", seed_path)
    seed_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_module)

    session = SessionLocal()
    try:
        count = seed_module.run_seed(session)
        print(f"✅ 成功导入 {count} 条样例讨论")
        return True
    except Exception as e:
        session.rollback()
        print(f"❌ 种子数据导入失败: {e}")
        return False
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="AI Panel Studio — 数据库初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/init_db.py                 # 创建所有表
  python scripts/init_db.py --drop          # 删除后重建
  python scripts/init_db.py --seed          # 创建表 + 导入样例数据
  python scripts/init_db.py --verify        # 验证表结构
        """,
    )
    parser.add_argument("--drop", action="store_true", help="删除所有表后重建")
    parser.add_argument("--seed", action="store_true", help="导入样例数据")
    parser.add_argument("--verify", action="store_true", help="仅验证表结构")

    args = parser.parse_args()

    print("🎯 AI Panel Studio — 数据库初始化")
    print(f"   数据库: sqlite:///{BACKEND_DIR / 'ai_panel_studio.db'}")
    print()

    if args.verify:
        verify_tables()
        return

    if args.drop:
        if not drop_tables():
            return

    create_tables()
    verify_tables()

    if args.seed:
        import_seed_data()

    print("\n✨ 数据库初始化完成。")


if __name__ == "__main__":
    main()

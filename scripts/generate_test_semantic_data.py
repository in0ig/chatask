#!/usr/bin/env python3
"""
生成测试用的语义数据（数据字典和知识库）

用于验证五模块语义增强系统
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy.orm import Session
from src.database import get_db, engine
from src.models.data_preparation_model import FieldMapping
from datetime import datetime

def generate_field_mappings(db: Session):
    """生成数据字典数据"""
    print("=" * 80)
    print("📝 生成数据字典数据")
    print("=" * 80)
    
    from src.models.data_preparation_model import TableField, DataTable
    
    # 首先获取 orders 和 users 表
    orders_table = db.query(DataTable).filter(
        DataTable.table_name == "orders"
    ).first()
    
    users_table = db.query(DataTable).filter(
        DataTable.table_name == "users"
    ).first()
    
    if not orders_table:
        print("⚠️ 警告: orders 表不存在，请先同步表结构")
        return
    
    if not users_table:
        print("⚠️ 警告: users 表不存在，请先同步表结构")
        return
    
    # 获取表的字段
    orders_fields = db.query(TableField).filter(
        TableField.table_id == orders_table.id
    ).all()
    
    users_fields = db.query(TableField).filter(
        TableField.table_id == users_table.id
    ).all()
    
    if not orders_fields:
        print(f"⚠️ 警告: orders 表 (ID: {orders_table.id}) 没有字段信息")
        return
    
    if not users_fields:
        print(f"⚠️ 警告: users 表 (ID: {users_table.id}) 没有字段信息")
        return
    
    # 构建字段名到字段对象的映射
    orders_field_map = {f.field_name: f for f in orders_fields}
    users_field_map = {f.field_name: f for f in users_fields}
    
    # Orders 表的字段映射配置
    orders_mappings_config = [
        {
            "field_name": "id",
            "business_name": "订单ID",
            "business_meaning": "订单的唯一标识符，主键"
        },
        {
            "field_name": "user_id",
            "business_name": "用户ID",
            "business_meaning": "下单用户的ID，关联到users表"
        },
        {
            "field_name": "product_name",
            "business_name": "产品名称",
            "business_meaning": "订单中的产品名称"
        },
        {
            "field_name": "amount",
            "business_name": "订单金额",
            "business_meaning": "订单的总金额，单位：元"
        },
        {
            "field_name": "created_at",
            "business_name": "创建时间",
            "business_meaning": "订单创建的时间戳"
        }
    ]
    
    # Users 表的字段映射配置
    users_mappings_config = [
        {
            "field_name": "id",
            "business_name": "用户ID",
            "business_meaning": "用户的唯一标识符，主键"
        },
        {
            "field_name": "name",
            "business_name": "用户姓名",
            "business_meaning": "用户的真实姓名"
        },
        {
            "field_name": "email",
            "business_name": "电子邮箱",
            "business_meaning": "用户的电子邮箱地址"
        },
        {
            "field_name": "created_at",
            "business_name": "注册时间",
            "business_meaning": "用户注册的时间戳"
        }
    ]
    
    # 删除旧的字段映射
    for field in orders_fields + users_fields:
        db.query(FieldMapping).filter(
            FieldMapping.field_id == field.id
        ).delete(synchronize_session=False)
    
    db.commit()
    
    # 创建 orders 表的字段映射
    created_count = 0
    for config in orders_mappings_config:
        field_name = config["field_name"]
        if field_name in orders_field_map:
            field = orders_field_map[field_name]
            mapping = FieldMapping(
                table_id=field.table_id,
                field_id=field.id,
                business_name=config["business_name"],
                business_meaning=config["business_meaning"],
                is_required=not field.is_nullable
            )
            db.add(mapping)
            created_count += 1
            print(f"✅ 添加字段映射: orders.{field_name} → {config['business_name']}")
        else:
            print(f"⚠️ 跳过: orders.{field_name} (字段不存在)")
    
    # 创建 users 表的字段映射
    for config in users_mappings_config:
        field_name = config["field_name"]
        if field_name in users_field_map:
            field = users_field_map[field_name]
            mapping = FieldMapping(
                table_id=field.table_id,
                field_id=field.id,
                business_name=config["business_name"],
                business_meaning=config["business_meaning"],
                is_required=not field.is_nullable
            )
            db.add(mapping)
            created_count += 1
            print(f"✅ 添加字段映射: users.{field_name} → {config['business_name']}")
        else:
            print(f"⚠️ 跳过: users.{field_name} (字段不存在)")
    
    db.commit()
    print(f"\n✅ 成功生成 {created_count} 条数据字典记录")
    print("=" * 80)


def generate_knowledge_base(db: Session):
    """生成知识库数据"""
    print("\n" + "=" * 80)
    print("📚 生成知识库数据")
    print("=" * 80)
    
    from src.models.knowledge_base_model import KnowledgeBase
    from src.models.knowledge_item_model import KnowledgeItem
    
    # 首先创建或获取知识库
    kb_orders = db.query(KnowledgeBase).filter(
        KnowledgeBase.name == "订单业务知识库"
    ).first()
    
    if not kb_orders:
        kb_orders = KnowledgeBase(
            name="订单业务知识库",
            description="关于订单和用户的业务知识",
            type="TERM",
            scope="TABLE",
            table_id="orders",
            status=True
        )
        db.add(kb_orders)
        db.commit()
        print(f"✅ 创建知识库: {kb_orders.name}")
    else:
        print(f"✅ 使用现有知识库: {kb_orders.name}")
    
    # 删除该知识库下的旧知识项
    db.query(KnowledgeItem).filter(
        KnowledgeItem.knowledge_base_id == kb_orders.id
    ).delete(synchronize_session=False)
    db.commit()
    
    # 创建知识项
    knowledge_items = [
        # 业务术语 (TERM)
        {
            "type": "TERM",
            "name": "订单金额",
            "explanation": "订单金额是指用户购买产品时需要支付的总金额，单位为人民币元。包含产品价格、运费等所有费用。",
            "example_question": "订单总金额是多少？"
        },
        {
            "type": "TERM",
            "name": "用户",
            "explanation": "用户是指在系统中注册并可以下单购买产品的个人或组织。每个用户有唯一的用户ID。",
            "example_question": "有多少个用户？"
        },
        
        # 业务逻辑 (LOGIC)
        {
            "type": "LOGIC",
            "name": None,  # LOGIC 类型不需要 name
            "explanation": "统计订单时，应该使用COUNT(*)统计订单数量，使用SUM(amount)统计订单总金额，使用AVG(amount)统计平均订单金额。",
            "example_question": "如何统计订单总数和总金额？"
        },
        {
            "type": "LOGIC",
            "name": None,
            "explanation": "查询用户的订单信息时，需要通过orders.user_id关联users.id。一个用户可以有多个订单。",
            "example_question": "如何查询某个用户的所有订单？"
        },
        {
            "type": "LOGIC",
            "name": None,
            "explanation": "订单金额必须大于0。如果查询到金额为0或负数的订单，说明数据存在异常。",
            "example_question": "如何检查订单金额的有效性？"
        },
        {
            "type": "LOGIC",
            "name": None,
            "explanation": "查询特定时间范围的订单时，使用created_at字段。例如：查询今天的订单用DATE(created_at) = CURDATE()，查询本月的订单用MONTH(created_at) = MONTH(CURDATE())。",
            "example_question": "如何查询今天的订单？"
        },
        
        # 业务事件 (EVENT)
        {
            "type": "EVENT",
            "name": None,
            "explanation": "当用户下单时，系统会在orders表中创建一条新记录，记录订单ID、用户ID、产品名称、金额和创建时间。",
            "example_question": None,
            "event_date_start": datetime.now()
        }
    ]
    
    # 插入知识项
    for item_data in knowledge_items:
        item = KnowledgeItem(
            knowledge_base_id=kb_orders.id,
            **item_data
        )
        db.add(item)
        type_name = item_data['type']
        name_or_desc = item_data.get('name') or item_data['explanation'][:50] + "..."
        print(f"✅ 添加知识项: [{type_name}] {name_or_desc}")
    
    db.commit()
    print(f"\n✅ 成功生成 {len(knowledge_items)} 条知识项记录")
    print("=" * 80)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 开始生成测试语义数据")
    print("=" * 80)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 生成数据字典
        generate_field_mappings(db)
        
        # 生成知识库
        generate_knowledge_base(db)
        
        print("\n" + "=" * 80)
        print("✅ 所有测试数据生成完成！")
        print("=" * 80)
        print("\n现在可以进行三轮对话测试：")
        print("1. 查询订单总数")
        print("2. 那订单总金额是多少？")
        print("3. 用户张三下了几单？")
        print("\n这将验证：")
        print("- 五模块语义增强系统")
        print("- 历史对话上下文管理")
        print("- 上下文聚合和摘要功能")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import uuid4

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.knowledge_base_model import KnowledgeBase
from services.database_service import get_db

def seed_knowledge_bases(db: Session):
    """填充知识库测试数据"""
    
    # 名词知识库
    term_knowledge_bases = [
        {
            "name": "毛利润",
            "description": "销售收入减去销售成本后的利润，反映产品直接盈利能力",
            "type": "TERM",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        },
        {
            "name": "转化率",
            "description": "完成目标行为的用户占总访问用户的比例，用于衡量营销效果",
            "type": "TERM",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        },
        {
            "name": "客单价",
            "description": "每个顾客平均购买商品的金额，用于评估客户价值",
            "type": "TERM",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        }
    ]
    
    # 业务逻辑知识库
    logic_knowledge_bases = [
        {
            "name": "默认查询时间范围",
            "description": "当用户未指定时间范围时，默认查询最近30天的数据",
            "type": "LOGIC",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        },
        {
            "name": "库存预警阈值",
            "description": "当库存量低于安全库存的20%时触发预警",
            "type": "LOGIC",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        },
        {
            "name": "绩效考核周期",
            "description": "员工绩效按月进行考核，每月1日生成上月绩效报告",
            "type": "LOGIC",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        }
    ]
    
    # 事件知识库
    event_knowledge_bases = [
        {
            "name": "2024年春节促销活动",
            "description": "2024年春节促销活动期间（1月25日至2月15日）的特殊销售规则",
            "type": "EVENT",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        },
        {
            "name": "系统升级维护",
            "description": "2024年系统升级维护期间（2月10日至2月12日）的数据处理规则",
            "type": "EVENT",
            "scope": "GLOBAL",
            "status": True,
            "table_id": None
        }
    ]
    
    # 合并所有知识库数据
    all_knowledge_bases = term_knowledge_bases + logic_knowledge_bases + event_knowledge_bases
    
    # 批量插入数据
    for kb_data in all_knowledge_bases:
        # 检查是否已存在
        existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == kb_data["name"]).first()
        if not existing:
            knowledge_base = KnowledgeBase(
                id=str(uuid4()),
                name=kb_data["name"],
                description=kb_data["description"],
                type=kb_data["type"],
                scope=kb_data["scope"],
                status=kb_data["status"],
                table_id=kb_data["table_id"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(knowledge_base)
    
    db.commit()
    print(f"成功填充 {len(all_knowledge_bases)} 条知识库数据")

if __name__ == "__main__":
    db = next(get_db())
    try:
        seed_knowledge_bases(db)
    except Exception as e:
        print(f"填充数据时出错: {e}")
        db.rollback()
    finally:
        db.close()
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(tags=["Query History"])

@router.get("/history", response_model=List[dict])
def get_query_history(db: Session = Depends(get_db)):
    """
    获取所有查询历史记录
    按创建时间降序排序
    """
    try:
        query = text("""
        SELECT id, query_text, result_data, chart_type, created_at 
        FROM query_history 
        ORDER BY created_at DESC
        """)
        results = db.execute(query).fetchall()
        
        # 格式化结果
        formatted_results = []
        for row in results:
            formatted_results.append({
                "id": row[0],
                "query_text": row[1],
                "result": row[2],
                "chart_type": row[3],
                "created_at": row[4]
            })
        
        logger.info(f"Retrieved {len(formatted_results)} history records")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error fetching query history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch query history")

@router.delete("/history")
def clear_all_history(db: Session = Depends(get_db)):
    """
    清空所有查询历史记录
    """
    try:
        query = text("DELETE FROM query_history")
        result = db.execute(query)
        deleted_count = result.rowcount
        
        db.commit()
        
        logger.info(f"Cleared {deleted_count} history records")
        return {"message": "All history cleared", "count": deleted_count}
        
    except Exception as e:
        logger.error(f"Error clearing all history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear history")

@router.delete("/history/{history_id}")
def delete_history_item(history_id: int, db: Session = Depends(get_db)):
    """
    删除单条查询历史记录
    """
    try:
        # 先检查记录是否存在
        check_query = text("SELECT id FROM query_history WHERE id = :id")
        existing_record = db.execute(check_query, {"id": history_id}).fetchone()
        
        if not existing_record:
            logger.warning(f"History record with id {history_id} not found")
            raise HTTPException(status_code=404, detail="History record not found")
        
        # 删除记录
        delete_query = text("DELETE FROM query_history WHERE id = :id")
        result = db.execute(delete_query, {"id": history_id})
        
        db.commit()
        
        logger.info(f"Deleted history record with id {history_id}")
        return {"message": "History deleted successfully"}
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"Error deleting history item {history_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete history record")
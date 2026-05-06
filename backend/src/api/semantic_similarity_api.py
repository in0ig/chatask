"""
语义相似度计算引擎 API

任务 5.2.2 的 API 接口实现
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from src.database import get_db
from src.services.semantic_similarity_engine import (
    SemanticSimilarityEngine,
    KeywordAnalysis,
    SemanticMatch
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/semantic-similarity", tags=["语义相似度"])

# 全局语义相似度引擎实例
similarity_engine = SemanticSimilarityEngine()


@router.post("/analyze-question", response_model=Dict[str, Any])
async def analyze_user_question(
    request: Dict[str, str],
    db: Session = Depends(get_db)
):
    """
    分析用户问题，提取关键词和语义信息
    
    任务 5.2.2 的第一个功能点：基于用户问题进行关键词提取和语义分析
    """
    try:
        user_question = request.get("user_question", "")
        if not user_question:
            raise HTTPException(status_code=400, detail="用户问题不能为空")
        
        # 分析用户问题
        keyword_analysis = similarity_engine.analyze_user_question(user_question)
        
        return {
            "success": True,
            "data": {
                "chinese_terms": keyword_analysis.chinese_terms,
                "english_terms": keyword_analysis.english_terms,
                "business_keywords": keyword_analysis.business_keywords,
                "technical_keywords": keyword_analysis.technical_keywords,
                "domain_keywords": keyword_analysis.domain_keywords,
                "all_keywords": list(keyword_analysis.all_keywords)
            },
            "message": f"成功分析用户问题，提取到 {len(keyword_analysis.all_keywords)} 个关键词"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"分析用户问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析用户问题失败: {str(e)}")


@router.post("/calculate-table-similarity", response_model=Dict[str, Any])
async def calculate_table_similarity(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    计算表的语义相似度
    
    任务 5.2.2 的第二个功能点：表名相似度计算
    """
    try:
        user_question = request.get("user_question", "")
        tables = request.get("tables", [])
        
        if not user_question:
            raise HTTPException(status_code=400, detail="用户问题不能为空")
        if not tables:
            raise HTTPException(status_code=400, detail="表信息不能为空")
        
        # 分析用户问题
        keyword_analysis = similarity_engine.analyze_user_question(user_question)
        
        # 计算每个表的相似度
        table_matches = []
        for table_info in tables:
            match = similarity_engine.calculate_table_similarity(keyword_analysis, table_info)
            table_matches.append({
                "table_id": match.target_id,
                "table_name": match.target_name,
                "similarity_score": match.similarity_score,
                "match_reasons": match.match_reasons,
                "matched_keywords": match.matched_keywords,
                "business_meaning": match.business_meaning
            })
        
        # 排序结果
        ranked_matches = similarity_engine.rank_semantic_matches(
            [SemanticMatch(
                target_id=m["table_id"],
                target_name=m["table_name"],
                target_type="table",
                similarity_score=m["similarity_score"],
                match_reasons=m["match_reasons"],
                matched_keywords=m["matched_keywords"],
                business_meaning=m["business_meaning"]
            ) for m in table_matches]
        )
        
        return {
            "success": True,
            "data": {
                "keyword_analysis": {
                    "chinese_terms": keyword_analysis.chinese_terms,
                    "english_terms": keyword_analysis.english_terms,
                    "business_keywords": keyword_analysis.business_keywords,
                    "technical_keywords": keyword_analysis.technical_keywords,
                    "domain_keywords": keyword_analysis.domain_keywords,
                    "all_keywords": list(keyword_analysis.all_keywords)
                },
                "table_matches": [{
                    "table_id": match.target_id,
                    "table_name": match.target_name,
                    "similarity_score": match.similarity_score,
                    "match_reasons": match.match_reasons,
                    "matched_keywords": match.matched_keywords,
                    "business_meaning": match.business_meaning
                } for match in ranked_matches]
            },
            "message": f"成功计算 {len(tables)} 个表的相似度，返回 {len(ranked_matches)} 个匹配结果"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"计算表相似度失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算表相似度失败: {str(e)}")


@router.post("/calculate-field-similarity", response_model=Dict[str, Any])
async def calculate_field_similarity(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    计算字段的语义相似度
    
    任务 5.2.2 的第二个功能点：字段名相似度计算
    """
    try:
        user_question = request.get("user_question", "")
        fields = request.get("fields", [])
        table_context = request.get("table_context")
        
        if not user_question:
            raise HTTPException(status_code=400, detail="用户问题不能为空")
        if not fields:
            raise HTTPException(status_code=400, detail="字段信息不能为空")
        
        # 分析用户问题
        keyword_analysis = similarity_engine.analyze_user_question(user_question)
        
        # 计算每个字段的相似度
        field_matches = []
        for field_info in fields:
            match = similarity_engine.calculate_field_similarity(
                keyword_analysis, field_info, table_context
            )
            field_matches.append(match)
        
        # 排序结果
        ranked_matches = similarity_engine.rank_semantic_matches(field_matches)
        
        return {
            "success": True,
            "data": {
                "keyword_analysis": {
                    "chinese_terms": keyword_analysis.chinese_terms,
                    "english_terms": keyword_analysis.english_terms,
                    "business_keywords": keyword_analysis.business_keywords,
                    "technical_keywords": keyword_analysis.technical_keywords,
                    "domain_keywords": keyword_analysis.domain_keywords,
                    "all_keywords": list(keyword_analysis.all_keywords)
                },
                "field_matches": [{
                    "field_id": match.target_id,
                    "field_name": match.target_name,
                    "similarity_score": match.similarity_score,
                    "match_reasons": match.match_reasons,
                    "matched_keywords": match.matched_keywords,
                    "business_meaning": match.business_meaning,
                    "technical_mapping": match.technical_mapping
                } for match in ranked_matches]
            },
            "message": f"成功计算 {len(fields)} 个字段的相似度，返回 {len(ranked_matches)} 个匹配结果"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"计算字段相似度失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算字段相似度失败: {str(e)}")


@router.post("/business-term-mapping", response_model=Dict[str, Any])
async def calculate_business_term_mapping(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    中文业务术语到技术字段的智能映射
    
    任务 5.2.2 的第三个功能点：支持中文业务术语到技术字段的智能映射
    """
    try:
        user_question = request.get("user_question", "")
        business_terms = request.get("business_terms", [])
        
        if not user_question:
            raise HTTPException(status_code=400, detail="用户问题不能为空")
        if not business_terms:
            raise HTTPException(status_code=400, detail="业务术语不能为空")
        
        # 分析用户问题
        keyword_analysis = similarity_engine.analyze_user_question(user_question)
        
        # 计算每个业务术语的相似度
        term_matches = []
        for business_term in business_terms:
            match = similarity_engine.calculate_business_term_similarity(
                keyword_analysis, business_term
            )
            term_matches.append(match)
        
        # 排序结果
        ranked_matches = similarity_engine.rank_semantic_matches(term_matches)
        
        return {
            "success": True,
            "data": {
                "keyword_analysis": {
                    "chinese_terms": keyword_analysis.chinese_terms,
                    "english_terms": keyword_analysis.english_terms,
                    "business_keywords": keyword_analysis.business_keywords,
                    "technical_keywords": keyword_analysis.technical_keywords,
                    "domain_keywords": keyword_analysis.domain_keywords,
                    "all_keywords": list(keyword_analysis.all_keywords)
                },
                "business_term_matches": [{
                    "term_id": match.target_id,
                    "term_name": match.target_name,
                    "similarity_score": match.similarity_score,
                    "match_reasons": match.match_reasons,
                    "matched_keywords": match.matched_keywords,
                    "business_meaning": match.business_meaning
                } for match in ranked_matches]
            },
            "message": f"成功计算 {len(business_terms)} 个业务术语的相似度，返回 {len(ranked_matches)} 个匹配结果"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"计算业务术语映射失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算业务术语映射失败: {str(e)}")


@router.post("/knowledge-term-matching", response_model=Dict[str, Any])
async def calculate_knowledge_term_matching(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    知识库术语的语义匹配和权重计算
    
    任务 5.2.2 的第四个功能点：添加知识库术语的语义匹配和权重计算
    """
    try:
        user_question = request.get("user_question", "")
        knowledge_items = request.get("knowledge_items", [])
        
        if not user_question:
            raise HTTPException(status_code=400, detail="用户问题不能为空")
        if not knowledge_items:
            raise HTTPException(status_code=400, detail="知识库项目不能为空")
        
        # 分析用户问题
        keyword_analysis = similarity_engine.analyze_user_question(user_question)
        
        # 计算每个知识库项目的相似度
        knowledge_matches = []
        for knowledge_item in knowledge_items:
            match = similarity_engine.calculate_knowledge_term_similarity(
                keyword_analysis, knowledge_item
            )
            knowledge_matches.append(match)
        
        # 排序结果
        ranked_matches = similarity_engine.rank_semantic_matches(knowledge_matches)
        
        return {
            "success": True,
            "data": {
                "keyword_analysis": {
                    "chinese_terms": keyword_analysis.chinese_terms,
                    "english_terms": keyword_analysis.english_terms,
                    "business_keywords": keyword_analysis.business_keywords,
                    "technical_keywords": keyword_analysis.technical_keywords,
                    "domain_keywords": keyword_analysis.domain_keywords,
                    "all_keywords": list(keyword_analysis.all_keywords)
                },
                "knowledge_matches": [{
                    "knowledge_id": match.target_id,
                    "knowledge_name": match.target_name,
                    "similarity_score": match.similarity_score,
                    "match_reasons": match.match_reasons,
                    "matched_keywords": match.matched_keywords,
                    "business_meaning": match.business_meaning
                } for match in ranked_matches]
            },
            "message": f"成功计算 {len(knowledge_items)} 个知识库项目的相似度，返回 {len(ranked_matches)} 个匹配结果"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"计算知识库术语匹配失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算知识库术语匹配失败: {str(e)}")


@router.post("/comprehensive-similarity", response_model=Dict[str, Any])
async def calculate_comprehensive_similarity(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    综合语义相似度计算
    
    整合表名、字段名、业务含义、知识库术语的多维度相似度计算
    """
    try:
        user_question = request.get("user_question", "")
        tables = request.get("tables", [])
        business_terms = request.get("business_terms", [])
        knowledge_items = request.get("knowledge_items", [])
        
        if not user_question:
            raise HTTPException(status_code=400, detail="用户问题不能为空")
        
        # 分析用户问题
        keyword_analysis = similarity_engine.analyze_user_question(user_question)
        
        results = {
            "keyword_analysis": {
                "chinese_terms": keyword_analysis.chinese_terms,
                "english_terms": keyword_analysis.english_terms,
                "business_keywords": keyword_analysis.business_keywords,
                "technical_keywords": keyword_analysis.technical_keywords,
                "domain_keywords": keyword_analysis.domain_keywords,
                "all_keywords": list(keyword_analysis.all_keywords)
            }
        }
        
        # 计算表相似度
        if tables:
            table_matches = []
            for table_info in tables:
                match = similarity_engine.calculate_table_similarity(keyword_analysis, table_info)
                table_matches.append(match)
            
            ranked_table_matches = similarity_engine.rank_semantic_matches(table_matches)
            results["table_matches"] = [{
                "table_id": match.target_id,
                "table_name": match.target_name,
                "similarity_score": match.similarity_score,
                "match_reasons": match.match_reasons,
                "matched_keywords": match.matched_keywords,
                "business_meaning": match.business_meaning
            } for match in ranked_table_matches]
        
        # 计算业务术语相似度
        if business_terms:
            term_matches = []
            for business_term in business_terms:
                match = similarity_engine.calculate_business_term_similarity(
                    keyword_analysis, business_term
                )
                term_matches.append(match)
            
            ranked_term_matches = similarity_engine.rank_semantic_matches(term_matches)
            results["business_term_matches"] = [{
                "term_id": match.target_id,
                "term_name": match.target_name,
                "similarity_score": match.similarity_score,
                "match_reasons": match.match_reasons,
                "matched_keywords": match.matched_keywords,
                "business_meaning": match.business_meaning
            } for match in ranked_term_matches]
        
        # 计算知识库术语相似度
        if knowledge_items:
            knowledge_matches = []
            for knowledge_item in knowledge_items:
                match = similarity_engine.calculate_knowledge_term_similarity(
                    keyword_analysis, knowledge_item
                )
                knowledge_matches.append(match)
            
            ranked_knowledge_matches = similarity_engine.rank_semantic_matches(knowledge_matches)
            results["knowledge_matches"] = [{
                "knowledge_id": match.target_id,
                "knowledge_name": match.target_name,
                "similarity_score": match.similarity_score,
                "match_reasons": match.match_reasons,
                "matched_keywords": match.matched_keywords,
                "business_meaning": match.business_meaning
            } for match in ranked_knowledge_matches]
        
        return {
            "success": True,
            "data": results,
            "message": "成功完成综合语义相似度计算"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"综合语义相似度计算失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"综合语义相似度计算失败: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_similarity_statistics():
    """获取语义相似度引擎统计信息"""
    try:
        stats = similarity_engine.get_similarity_statistics()
        
        return {
            "success": True,
            "data": stats,
            "message": "成功获取语义相似度引擎统计信息"
        }
        
    except HTTPException:
        # 重新抛出 HTTPException，不要被通用异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """健康检查"""
    return {
        "success": True,
        "data": {
            "service": "semantic_similarity_engine",
            "status": "healthy",
            "version": "1.0.0"
        },
        "message": "语义相似度计算引擎运行正常"
    }
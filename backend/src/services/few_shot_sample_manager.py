# -*- coding: utf-8 -*-
"""
增强版Few-Shot样本管理系统
实现基于语义相似度的动态样本选择、自动验证、评分和质量管理
"""

import os
import json
import re
import math
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

from src.utils import logger


class SampleType(Enum):
    """样本类型"""
    POSITIVE = "positive"  # 正面样本（好的示例）
    NEGATIVE = "negative"  # 负面样本（错误示例）
    EDGE_CASE = "edge_case"  # 边界情况
    TEMPLATE = "template"  # 模板样本


class SampleStatus(Enum):
    """样本状态"""
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


@dataclass
class SampleMetrics:
    """样本指标"""
    usage_count: int = 0
    success_rate: float = 0.0
    avg_similarity_score: float = 0.0
    user_feedback_score: float = 0.0
    last_used: Optional[datetime] = None
    validation_score: float = 0.0
    
    def update_usage(self, success: bool, similarity_score: float, 
                    user_feedback: Optional[float] = None):
        """更新使用指标"""
        self.usage_count += 1
        self.last_used = datetime.now()
        
        # 更新成功率
        current_success_count = int(self.success_rate * (self.usage_count - 1))
        if success:
            current_success_count += 1
        self.success_rate = current_success_count / self.usage_count
        
        # 更新平均相似度分数
        total_similarity = self.avg_similarity_score * (self.usage_count - 1) + similarity_score
        self.avg_similarity_score = total_similarity / self.usage_count
        
        # 更新用户反馈分数
        if user_feedback is not None:
            if self.user_feedback_score == 0:
                self.user_feedback_score = user_feedback
            else:
                self.user_feedback_score = (self.user_feedback_score + user_feedback) / 2


@dataclass
class FewShotSample:
    """Few-Shot样本"""
    sample_id: str
    prompt_type: str
    input_text: str
    output_text: str
    sample_type: SampleType = SampleType.POSITIVE
    status: SampleStatus = SampleStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: SampleMetrics = field(default_factory=SampleMetrics)
    validation_notes: str = ""
    
    def __post_init__(self):
        if not self.sample_id:
            self.sample_id = f"{self.prompt_type}_{int(datetime.now().timestamp())}"


class SemanticSimilarityCalculator:
    """语义相似度计算器"""
    
    def __init__(self):
        # 简化的TF-IDF实现
        self.vocabulary: Set[str] = set()
        self.idf_scores: Dict[str, float] = {}
        
    def _tokenize(self, text: str) -> List[str]:
        """文本分词"""
        # 简单的分词实现
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        return [token for token in tokens if len(token) > 1]
    
    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """计算词频"""
        tf = Counter(tokens)
        total_tokens = len(tokens)
        return {word: count / total_tokens for word, count in tf.items()}
    
    def _calculate_idf(self, documents: List[List[str]]) -> Dict[str, float]:
        """计算逆文档频率"""
        doc_count = len(documents)
        word_doc_count = defaultdict(int)
        
        for doc in documents:
            unique_words = set(doc)
            for word in unique_words:
                word_doc_count[word] += 1
        
        idf = {}
        for word, count in word_doc_count.items():
            idf[word] = math.log(doc_count / count)
        
        return idf
    
    def calculate_similarity(self, text1: str, text2: str, 
                           reference_corpus: Optional[List[str]] = None) -> float:
        """计算两个文本的语义相似度"""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # 如果提供了参考语料库，使用TF-IDF
        if reference_corpus:
            all_docs = [self._tokenize(doc) for doc in reference_corpus] + [tokens1, tokens2]
            idf_scores = self._calculate_idf(all_docs)
            
            tf1 = self._calculate_tf(tokens1)
            tf2 = self._calculate_tf(tokens2)
            
            # 计算TF-IDF向量
            all_words = set(tokens1 + tokens2)
            vector1 = [tf1.get(word, 0) * idf_scores.get(word, 0) for word in all_words]
            vector2 = [tf2.get(word, 0) * idf_scores.get(word, 0) for word in all_words]
            
            # 计算余弦相似度
            dot_product = sum(a * b for a, b in zip(vector1, vector2))
            magnitude1 = math.sqrt(sum(a * a for a in vector1))
            magnitude2 = math.sqrt(sum(b * b for b in vector2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        else:
            # 简单的Jaccard相似度
            set1 = set(tokens1)
            set2 = set(tokens2)
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0.0
    
    def find_most_similar(self, query_text: str, candidate_texts: List[str],
                         top_k: int = 5) -> List[Tuple[int, float]]:
        """找到最相似的文本"""
        similarities = []
        
        for i, candidate in enumerate(candidate_texts):
            similarity = self.calculate_similarity(query_text, candidate, candidate_texts)
            similarities.append((i, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


class SampleValidator:
    """样本验证器"""
    
    def __init__(self):
        self.validation_rules = {
            'min_input_length': 10,
            'min_output_length': 5,
            'max_input_length': 2000,
            'max_output_length': 5000,
            'forbidden_patterns': [
                r'<script.*?>.*?</script>',  # 防止脚本注入
                r'javascript:',
                r'data:text/html'
            ]
        }
    
    def validate_sample(self, sample: FewShotSample) -> Tuple[bool, List[str]]:
        """验证样本质量"""
        errors = []
        
        # 检查输入长度
        if len(sample.input_text) < self.validation_rules['min_input_length']:
            errors.append(f"输入文本过短（最少{self.validation_rules['min_input_length']}字符）")
        
        if len(sample.input_text) > self.validation_rules['max_input_length']:
            errors.append(f"输入文本过长（最多{self.validation_rules['max_input_length']}字符）")
        
        # 检查输出长度
        if len(sample.output_text) < self.validation_rules['min_output_length']:
            errors.append(f"输出文本过短（最少{self.validation_rules['min_output_length']}字符）")
        
        if len(sample.output_text) > self.validation_rules['max_output_length']:
            errors.append(f"输出文本过长（最多{self.validation_rules['max_output_length']}字符）")
        
        # 检查禁用模式
        for pattern in self.validation_rules['forbidden_patterns']:
            if re.search(pattern, sample.input_text, re.IGNORECASE):
                errors.append(f"输入文本包含禁用模式: {pattern}")
            if re.search(pattern, sample.output_text, re.IGNORECASE):
                errors.append(f"输出文本包含禁用模式: {pattern}")
        
        # 检查JSON格式（如果输出应该是JSON）
        if sample.prompt_type in ['intent_recognition', 'table_selection', 'sql_generation']:
            try:
                json.loads(sample.output_text)
            except json.JSONDecodeError:
                errors.append("输出文本不是有效的JSON格式")
        
        # 计算验证分数
        validation_score = max(0.0, 1.0 - len(errors) * 0.2)
        sample.metrics.validation_score = validation_score
        
        return len(errors) == 0, errors
    
    def auto_fix_sample(self, sample: FewShotSample) -> FewShotSample:
        """自动修复样本"""
        # 清理输入文本
        sample.input_text = sample.input_text.strip()
        sample.output_text = sample.output_text.strip()
        
        # 移除禁用模式
        for pattern in self.validation_rules['forbidden_patterns']:
            sample.input_text = re.sub(pattern, '', sample.input_text, flags=re.IGNORECASE)
            sample.output_text = re.sub(pattern, '', sample.output_text, flags=re.IGNORECASE)
        
        # 截断过长的文本
        if len(sample.input_text) > self.validation_rules['max_input_length']:
            sample.input_text = sample.input_text[:self.validation_rules['max_input_length']] + "..."
        
        if len(sample.output_text) > self.validation_rules['max_output_length']:
            sample.output_text = sample.output_text[:self.validation_rules['max_output_length']] + "..."
        
        return sample


class EnhancedFewShotManager:
    """增强版Few-Shot样本管理器"""
    
    def __init__(self, samples_path: str = "backend/config/enhanced_few_shot_samples.json"):
        self.samples_path = samples_path
        self.samples: Dict[str, List[FewShotSample]] = defaultdict(list)
        self.similarity_calculator = SemanticSimilarityCalculator()
        self.validator = SampleValidator()
        
        # 加载样本
        self._load_samples()
        
        logger.info(f"Enhanced few-shot manager initialized with {sum(len(samples) for samples in self.samples.values())} samples")
    
    def _load_samples(self) -> None:
        """加载样本数据"""
        try:
            if os.path.exists(self.samples_path):
                with open(self.samples_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for prompt_type, samples_data in data.items():
                    for sample_data in samples_data:
                        sample = FewShotSample(
                            sample_id=sample_data['sample_id'],
                            prompt_type=sample_data['prompt_type'],
                            input_text=sample_data['input_text'],
                            output_text=sample_data['output_text'],
                            sample_type=SampleType(sample_data.get('sample_type', 'positive')),
                            status=SampleStatus(sample_data.get('status', 'draft')),
                            created_at=datetime.fromisoformat(sample_data['created_at']),
                            created_by=sample_data.get('created_by', 'system'),
                            description=sample_data.get('description', ''),
                            tags=sample_data.get('tags', []),
                            metadata=sample_data.get('metadata', {}),
                            validation_notes=sample_data.get('validation_notes', '')
                        )
                        
                        # 加载指标
                        if 'metrics' in sample_data:
                            metrics_data = sample_data['metrics']
                            sample.metrics = SampleMetrics(
                                usage_count=metrics_data.get('usage_count', 0),
                                success_rate=metrics_data.get('success_rate', 0.0),
                                avg_similarity_score=metrics_data.get('avg_similarity_score', 0.0),
                                user_feedback_score=metrics_data.get('user_feedback_score', 0.0),
                                last_used=datetime.fromisoformat(metrics_data['last_used']) if metrics_data.get('last_used') else None,
                                validation_score=metrics_data.get('validation_score', 0.0)
                            )
                        
                        self.samples[prompt_type].append(sample)
            else:
                # 创建默认样本
                self._create_default_samples()
        
        except Exception as e:
            logger.error(f"Error loading enhanced few-shot samples: {str(e)}")
    
    def _save_samples(self) -> None:
        """保存样本数据"""
        try:
            data = {}
            
            for prompt_type, samples in self.samples.items():
                data[prompt_type] = []
                for sample in samples:
                    sample_data = {
                        'sample_id': sample.sample_id,
                        'prompt_type': sample.prompt_type,
                        'input_text': sample.input_text,
                        'output_text': sample.output_text,
                        'sample_type': sample.sample_type.value,
                        'status': sample.status.value,
                        'created_at': sample.created_at.isoformat(),
                        'created_by': sample.created_by,
                        'description': sample.description,
                        'tags': sample.tags,
                        'metadata': sample.metadata,
                        'validation_notes': sample.validation_notes,
                        'metrics': {
                            'usage_count': sample.metrics.usage_count,
                            'success_rate': sample.metrics.success_rate,
                            'avg_similarity_score': sample.metrics.avg_similarity_score,
                            'user_feedback_score': sample.metrics.user_feedback_score,
                            'last_used': sample.metrics.last_used.isoformat() if sample.metrics.last_used else None,
                            'validation_score': sample.metrics.validation_score
                        }
                    }
                    data[prompt_type].append(sample_data)
            
            os.makedirs(os.path.dirname(self.samples_path), exist_ok=True)
            with open(self.samples_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving enhanced few-shot samples: {str(e)}")
    
    def _create_default_samples(self) -> None:
        """创建默认样本"""
        default_samples = [
            # SQL生成样本
            FewShotSample(
                sample_id="sql_gen_001",
                prompt_type="sql_generation",
                input_text="查询所有用户的姓名和邮箱地址",
                output_text='{"sql": "SELECT name, email FROM users;", "explanation": "查询users表中的name和email字段", "estimatedRows": "未知"}',
                sample_type=SampleType.POSITIVE,
                status=SampleStatus.VALIDATED,
                description="基础查询示例",
                tags=["basic", "select", "users"]
            ),
            FewShotSample(
                sample_id="sql_gen_002",
                prompt_type="sql_generation",
                input_text="统计每个部门的员工数量，按数量降序排列",
                output_text='{"sql": "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department ORDER BY employee_count DESC;", "explanation": "按部门分组统计员工数量并降序排列", "estimatedRows": "部门数量"}',
                sample_type=SampleType.POSITIVE,
                status=SampleStatus.VALIDATED,
                description="分组统计示例",
                tags=["group_by", "count", "order_by"]
            ),
            
            # 意图识别样本
            FewShotSample(
                sample_id="intent_001",
                prompt_type="intent_recognition",
                input_text="显示销售额最高的产品",
                output_text='{"intent": "query", "confidence": 0.9, "reasoning": "用户想要查询具体的销售数据，属于智能问数类型"}',
                sample_type=SampleType.POSITIVE,
                status=SampleStatus.VALIDATED,
                description="查询意图示例",
                tags=["query", "sales", "product"]
            ),
            FewShotSample(
                sample_id="intent_002",
                prompt_type="intent_recognition",
                input_text="生成本月的销售报告",
                output_text='{"intent": "report", "confidence": 0.95, "reasoning": "用户要求生成综合性报告，属于生成报告类型"}',
                sample_type=SampleType.POSITIVE,
                status=SampleStatus.VALIDATED,
                description="报告意图示例",
                tags=["report", "monthly", "sales"]
            )
        ]
        
        for sample in default_samples:
            self.samples[sample.prompt_type].append(sample)
        
        self._save_samples()
        logger.info("Created default enhanced few-shot samples")
    
    def add_sample(self, prompt_type: str, input_text: str, output_text: str,
                  sample_type: SampleType = SampleType.POSITIVE,
                  description: str = "", tags: List[str] = None,
                  created_by: str = "system") -> Tuple[bool, List[str]]:
        """添加新样本"""
        sample = FewShotSample(
            sample_id="",  # 将在__post_init__中生成
            prompt_type=prompt_type,
            input_text=input_text,
            output_text=output_text,
            sample_type=sample_type,
            description=description,
            tags=tags or [],
            created_by=created_by
        )
        
        # 验证样本
        is_valid, errors = self.validator.validate_sample(sample)
        
        if is_valid:
            sample.status = SampleStatus.VALIDATED
            self.samples[prompt_type].append(sample)
            self._save_samples()
            logger.info(f"Added new sample: {sample.sample_id}")
            return True, []
        else:
            # 尝试自动修复
            fixed_sample = self.validator.auto_fix_sample(sample)
            is_valid_after_fix, errors_after_fix = self.validator.validate_sample(fixed_sample)
            
            if is_valid_after_fix:
                fixed_sample.status = SampleStatus.VALIDATED
                fixed_sample.validation_notes = f"Auto-fixed: {'; '.join(errors)}"
                self.samples[prompt_type].append(fixed_sample)
                self._save_samples()
                logger.info(f"Added auto-fixed sample: {fixed_sample.sample_id}")
                return True, [f"Auto-fixed: {'; '.join(errors)}"]
            else:
                logger.warning(f"Failed to add sample: {errors_after_fix}")
                return False, errors_after_fix
    
    def get_similar_samples(self, prompt_type: str, query_text: str,
                           max_samples: int = 3,
                           min_similarity: float = 0.3,
                           sample_types: List[SampleType] = None) -> List[Tuple[FewShotSample, float]]:
        """获取相似样本"""
        if prompt_type not in self.samples:
            return []
        
        # 过滤样本
        candidate_samples = []
        for sample in self.samples[prompt_type]:
            if sample.status not in [SampleStatus.ACTIVE, SampleStatus.VALIDATED]:
                continue
            
            if sample_types and sample.sample_type not in sample_types:
                continue
            
            candidate_samples.append(sample)
        
        if not candidate_samples:
            return []
        
        # 计算相似度
        candidate_texts = [sample.input_text for sample in candidate_samples]
        similarities = self.similarity_calculator.find_most_similar(
            query_text, candidate_texts, top_k=len(candidate_samples)
        )
        
        # 过滤并返回结果
        results = []
        for idx, similarity_score in similarities:
            if similarity_score >= min_similarity and len(results) < max_samples:
                sample = candidate_samples[idx]
                results.append((sample, similarity_score))
                
                # 更新使用统计
                sample.metrics.update_usage(True, similarity_score)
        
        if results:
            self._save_samples()
        
        return results
    
    def get_best_samples(self, prompt_type: str, max_samples: int = 5,
                        sample_types: List[SampleType] = None) -> List[FewShotSample]:
        """获取最佳样本（基于综合评分）"""
        if prompt_type not in self.samples:
            return []
        
        # 过滤样本
        candidate_samples = []
        for sample in self.samples[prompt_type]:
            if sample.status not in [SampleStatus.ACTIVE, SampleStatus.VALIDATED]:
                continue
            
            if sample_types and sample.sample_type not in sample_types:
                continue
            
            candidate_samples.append(sample)
        
        # 计算综合评分
        def calculate_score(sample: FewShotSample) -> float:
            # 综合评分 = 验证分数 * 0.3 + 成功率 * 0.3 + 用户反馈 * 0.2 + 使用频率 * 0.2
            usage_score = min(1.0, sample.metrics.usage_count / 100)  # 标准化使用次数
            
            return (
                sample.metrics.validation_score * 0.3 +
                sample.metrics.success_rate * 0.3 +
                sample.metrics.user_feedback_score * 0.2 +
                usage_score * 0.2
            )
        
        # 按评分排序
        scored_samples = [(sample, calculate_score(sample)) for sample in candidate_samples]
        scored_samples.sort(key=lambda x: x[1], reverse=True)
        
        return [sample for sample, score in scored_samples[:max_samples]]
    
    def update_sample_feedback(self, sample_id: str, success: bool,
                              user_feedback: Optional[float] = None) -> bool:
        """更新样本反馈"""
        for samples in self.samples.values():
            for sample in samples:
                if sample.sample_id == sample_id:
                    sample.metrics.update_usage(success, 0.0, user_feedback)
                    self._save_samples()
                    logger.debug(f"Updated feedback for sample: {sample_id}")
                    return True
        
        logger.warning(f"Sample not found: {sample_id}")
        return False
    
    def get_sample_statistics(self, prompt_type: Optional[str] = None) -> Dict[str, Any]:
        """获取样本统计信息"""
        if prompt_type:
            samples = self.samples.get(prompt_type, [])
        else:
            samples = [sample for sample_list in self.samples.values() for sample in sample_list]
        
        if not samples:
            return {"total_samples": 0}
        
        # 统计信息
        total_samples = len(samples)
        status_counts = Counter(sample.status.value for sample in samples)
        type_counts = Counter(sample.sample_type.value for sample in samples)
        
        # 质量指标
        validation_scores = [sample.metrics.validation_score for sample in samples if sample.metrics.validation_score > 0]
        success_rates = [sample.metrics.success_rate for sample in samples if sample.metrics.usage_count > 0]
        feedback_scores = [sample.metrics.user_feedback_score for sample in samples if sample.metrics.user_feedback_score > 0]
        
        return {
            "total_samples": total_samples,
            "status_distribution": dict(status_counts),
            "type_distribution": dict(type_counts),
            "quality_metrics": {
                "avg_validation_score": statistics.mean(validation_scores) if validation_scores else 0.0,
                "avg_success_rate": statistics.mean(success_rates) if success_rates else 0.0,
                "avg_user_feedback": statistics.mean(feedback_scores) if feedback_scores else 0.0,
                "samples_with_usage": len(success_rates),
                "samples_with_feedback": len(feedback_scores)
            },
            "recent_activity": {
                "samples_added_last_week": len([
                    s for s in samples 
                    if s.created_at > datetime.now() - timedelta(days=7)
                ]),
                "samples_used_last_week": len([
                    s for s in samples 
                    if s.metrics.last_used and s.metrics.last_used > datetime.now() - timedelta(days=7)
                ])
            }
        }
    
    def cleanup_low_quality_samples(self, min_validation_score: float = 0.5,
                                   min_success_rate: float = 0.3,
                                   min_usage_count: int = 5) -> int:
        """清理低质量样本"""
        removed_count = 0
        
        for prompt_type, samples in self.samples.items():
            samples_to_remove = []
            
            for sample in samples:
                # 跳过新样本（使用次数不足）
                if sample.metrics.usage_count < min_usage_count:
                    continue
                
                # 检查质量指标
                if (sample.metrics.validation_score < min_validation_score or
                    sample.metrics.success_rate < min_success_rate):
                    samples_to_remove.append(sample)
            
            # 移除低质量样本
            for sample in samples_to_remove:
                samples.remove(sample)
                removed_count += 1
                logger.info(f"Removed low-quality sample: {sample.sample_id}")
        
        if removed_count > 0:
            self._save_samples()
        
        return removed_count


# 全局实例
enhanced_few_shot_manager = EnhancedFewShotManager()

# 导出主要类和函数
__all__ = [
    "EnhancedFewShotManager",
    "FewShotSample",
    "SampleType",
    "SampleStatus",
    "SampleMetrics",
    "SemanticSimilarityCalculator",
    "SampleValidator",
    "enhanced_few_shot_manager"
]
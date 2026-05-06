"""
本地数据分析引擎服务

基于本地OpenAI模型实现数据追问和分析，确保查询结果数据完全不发送到云端。
支持数据对比、趋势分析、异常检测等功能。
"""

from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
import statistics
from openai import AsyncOpenAI


@dataclass
class QueryResult:
    """查询结果数据类"""
    query_id: str
    sql: str
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    executed_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query_id": self.query_id,
            "sql": self.sql,
            "data": self.data,
            "columns": self.columns,
            "row_count": self.row_count,
            "executed_at": self.executed_at.isoformat()
        }


@dataclass
class AnalysisContext:
    """分析上下文数据类"""
    current_result: QueryResult
    previous_results: List[QueryResult]
    conversation_history: List[Dict[str, str]]
    user_question: str
    
    def get_data_summary(self) -> str:
        """获取数据摘要（用于Prompt）"""
        summary = f"当前查询结果：\n"
        summary += f"- 列名：{', '.join(self.current_result.columns)}\n"
        summary += f"- 行数：{self.current_result.row_count}\n"
        
        if self.current_result.row_count > 0:
            # 显示前几行数据
            sample_size = min(5, self.current_result.row_count)
            summary += f"- 前{sample_size}行数据：\n"
            for i, row in enumerate(self.current_result.data[:sample_size]):
                summary += f"  {i+1}. {json.dumps(row, ensure_ascii=False)}\n"
        
        # 添加历史查询摘要
        if self.previous_results:
            summary += f"\n历史查询结果（共{len(self.previous_results)}个）：\n"
            for i, result in enumerate(self.previous_results[-3:]):  # 只显示最近3个
                summary += f"  {i+1}. {result.row_count}行数据，列：{', '.join(result.columns)}\n"
        
        return summary


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    analysis_id: str
    question: str
    answer: str
    insights: List[str]
    data_points: List[Dict[str, Any]]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "analysis_id": self.analysis_id,
            "question": self.question,
            "answer": self.answer,
            "insights": self.insights,
            "data_points": self.data_points,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class TimeSeriesData:
    """时间序列数据类"""
    timestamps: List[datetime]
    values: List[float]
    column_name: str
    
    def get_trend(self) -> str:
        """获取趋势方向"""
        if len(self.values) < 2:
            return "insufficient_data"
        
        # 简单线性趋势判断
        first_half_avg = statistics.mean(self.values[:len(self.values)//2])
        second_half_avg = statistics.mean(self.values[len(self.values)//2:])
        
        if second_half_avg > first_half_avg * 1.1:
            return "increasing"
        elif second_half_avg < first_half_avg * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def detect_anomalies(self, threshold: float = 2.0) -> List[int]:
        """检测异常值（基于标准差）"""
        if len(self.values) < 3:
            return []
        
        mean = statistics.mean(self.values)
        stdev = statistics.stdev(self.values)
        
        anomalies = []
        for i, value in enumerate(self.values):
            if abs(value - mean) > threshold * stdev:
                anomalies.append(i)
        
        return anomalies


@dataclass
class ComparisonResult:
    """数据对比结果类"""
    comparison_id: str
    current_summary: Dict[str, Any]
    previous_summary: Dict[str, Any]
    differences: List[Dict[str, Any]]
    insights: List[str]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "comparison_id": self.comparison_id,
            "current_summary": self.current_summary,
            "previous_summary": self.previous_summary,
            "differences": self.differences,
            "insights": self.insights,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class TrendAnalysisResult:
    """趋势分析结果类"""
    analysis_id: str
    column_name: str
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-1
    anomalies: List[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    insights: List[str]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "analysis_id": self.analysis_id,
            "column_name": self.column_name,
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
            "anomalies": self.anomalies,
            "predictions": self.predictions,
            "insights": self.insights,
            "created_at": self.created_at.isoformat()
        }


class LocalDataAnalyzer:
    """本地数据分析引擎"""
    
    def __init__(
        self,
        openai_api_key: str,
        openai_base_url: str = "http://localhost:11434/v1",  # 默认使用本地Ollama
        model_name: str = "qwen2.5:latest",
        max_tokens: int = 2000,
        temperature: float = 0.7
    ):
        """
        初始化本地数据分析引擎
        
        Args:
            openai_api_key: OpenAI API密钥（本地模型可以使用任意值）
            openai_base_url: OpenAI API基础URL（指向本地模型服务）
            model_name: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
        """
        self.client = AsyncOpenAI(
            api_key=openai_api_key,
            base_url=openai_base_url
        )
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 统计信息
        self.stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
    
    def _build_analysis_prompt(self, context: AnalysisContext) -> str:
        """
        构建数据分析Prompt
        
        Args:
            context: 分析上下文
            
        Returns:
            Prompt字符串
        """
        prompt = f"""你是一个专业的数据分析助手。用户刚刚执行了一个SQL查询并获得了结果数据。
现在用户想要对这些数据进行进一步的分析和理解。

{context.get_data_summary()}

用户的问题：{context.user_question}

请基于上述查询结果数据，回答用户的问题。你的回答应该：
1. 直接回答用户的问题
2. 提供数据洞察和发现
3. 如果适用，指出数据中的趋势、异常或模式
4. 使用清晰、专业的语言
5. 如果数据不足以回答问题，请说明原因

注意：
- 你只能基于提供的查询结果数据进行分析
- 不要编造或假设不存在的数据
- 如果需要更多数据，请明确说明需要什么样的数据
"""
        
        # 添加对话历史
        if context.conversation_history:
            prompt += "\n\n对话历史：\n"
            for msg in context.conversation_history[-5:]:  # 只包含最近5轮对话
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt += f"{role}: {content}\n"
        
        return prompt
    
    async def analyze_data(
        self,
        context: AnalysisContext,
        stream: bool = False
    ) -> AnalysisResult:
        """
        分析数据并回答用户问题
        
        Args:
            context: 分析上下文
            stream: 是否使用流式响应
            
        Returns:
            分析结果
        """
        start_time = datetime.now()
        
        try:
            # 构建Prompt
            prompt = self._build_analysis_prompt(context)
            
            # 调用本地模型
            messages = [
                {"role": "system", "content": "你是一个专业的数据分析助手，擅长从数据中发现洞察和趋势。"},
                {"role": "user", "content": prompt}
            ]
            
            if stream:
                # 流式响应将在另一个方法中处理
                raise ValueError("请使用 analyze_data_stream 方法进行流式分析")
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # 提取回答
            answer = response.choices[0].message.content
            
            # 提取洞察（简单实现：从回答中提取要点）
            insights = self._extract_insights(answer)
            
            # 提取数据点（如果回答中提到了具体数值）
            data_points = self._extract_data_points(answer, context.current_result)
            
            # 创建分析结果
            result = AnalysisResult(
                analysis_id=f"analysis_{datetime.now().timestamp()}",
                question=context.user_question,
                answer=answer,
                insights=insights,
                data_points=data_points,
                created_at=datetime.now()
            )
            
            # 更新统计
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            self.stats["total_analyses"] += 1
            self.stats["successful_analyses"] += 1
            self.stats["total_tokens_used"] += response.usage.total_tokens
            
            # 更新平均响应时间
            total = self.stats["total_analyses"]
            avg = self.stats["average_response_time"]
            self.stats["average_response_time"] = (avg * (total - 1) + response_time) / total
            
            return result
            
        except Exception as e:
            self.stats["total_analyses"] += 1
            self.stats["failed_analyses"] += 1
            raise Exception(f"数据分析失败: {str(e)}")
    
    async def analyze_data_stream(
        self,
        context: AnalysisContext
    ) -> AsyncGenerator[str, None]:
        """
        流式分析数据并回答用户问题
        
        Args:
            context: 分析上下文
            
        Yields:
            分析结果的文本片段
        """
        try:
            # 构建Prompt
            prompt = self._build_analysis_prompt(context)
            
            # 调用本地模型（流式）
            messages = [
                {"role": "system", "content": "你是一个专业的数据分析助手，擅长从数据中发现洞察和趋势。"},
                {"role": "user", "content": prompt}
            ]
            
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            # 更新统计
            self.stats["total_analyses"] += 1
            self.stats["successful_analyses"] += 1
            
        except Exception as e:
            self.stats["total_analyses"] += 1
            self.stats["failed_analyses"] += 1
            yield f"\n\n[错误] 数据分析失败: {str(e)}"
    
    def _extract_insights(self, answer: str) -> List[str]:
        """
        从回答中提取洞察
        
        Args:
            answer: AI回答
            
        Returns:
            洞察列表
        """
        insights = []
        
        # 简单实现：查找包含关键词的句子
        keywords = ["发现", "趋势", "异常", "模式", "洞察", "显示", "表明", "说明"]
        
        sentences = answer.split("。")
        for sentence in sentences:
            for keyword in keywords:
                if keyword in sentence and len(sentence.strip()) > 10:
                    insights.append(sentence.strip() + "。")
                    break
        
        return insights[:5]  # 最多返回5个洞察
    
    def _extract_data_points(
        self,
        answer: str,
        result: QueryResult
    ) -> List[Dict[str, Any]]:
        """
        从回答中提取提到的数据点
        
        Args:
            answer: AI回答
            result: 查询结果
            
        Returns:
            数据点列表
        """
        data_points = []
        
        # 简单实现：如果回答中提到了某一行的数据，将其标记为数据点
        # 这里只是一个占位实现，实际可以更复杂
        
        return data_points
    
    async def compare_data(
        self,
        current_result: QueryResult,
        previous_result: QueryResult,
        comparison_question: str
    ) -> AnalysisResult:
        """
        对比两个查询结果
        
        Args:
            current_result: 当前查询结果
            previous_result: 之前的查询结果
            comparison_question: 对比问题
            
        Returns:
            分析结果
        """
        # 构建对比上下文
        context = AnalysisContext(
            current_result=current_result,
            previous_results=[previous_result],
            conversation_history=[],
            user_question=comparison_question
        )
        
        # 修改Prompt以强调对比
        prompt = f"""你是一个专业的数据分析助手。用户想要对比两个查询结果。

当前查询结果：
- 列名：{', '.join(current_result.columns)}
- 行数：{current_result.row_count}
- 数据样本：{json.dumps(current_result.data[:3], ensure_ascii=False)}

之前的查询结果：
- 列名：{', '.join(previous_result.columns)}
- 行数：{previous_result.row_count}
- 数据样本：{json.dumps(previous_result.data[:3], ensure_ascii=False)}

用户的对比问题：{comparison_question}

请对比这两个查询结果，回答用户的问题。重点关注：
1. 数据的变化和差异
2. 趋势的变化
3. 异常值的出现或消失
4. 任何值得注意的模式变化
"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的数据分析助手，擅长数据对比和趋势分析。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        answer = response.choices[0].message.content
        insights = self._extract_insights(answer)
        
        return AnalysisResult(
            analysis_id=f"comparison_{datetime.now().timestamp()}",
            question=comparison_question,
            answer=answer,
            insights=insights,
            data_points=[],
            created_at=datetime.now()
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
    
    async def analyze_time_series(
        self,
        result: QueryResult,
        time_column: str,
        value_column: str,
        predict_steps: int = 3
    ) -> TrendAnalysisResult:
        """
        分析时间序列数据
        
        Args:
            result: 查询结果
            time_column: 时间列名
            value_column: 数值列名
            predict_steps: 预测步数
            
        Returns:
            趋势分析结果
        """
        try:
            # 提取时间序列数据
            timestamps = []
            values = []
            
            for row in result.data:
                if time_column in row and value_column in row:
                    # 尝试解析时间
                    time_val = row[time_column]
                    if isinstance(time_val, str):
                        try:
                            time_val = datetime.fromisoformat(time_val)
                        except:
                            continue
                    
                    # 尝试解析数值
                    try:
                        value = float(row[value_column])
                        timestamps.append(time_val)
                        values.append(value)
                    except:
                        continue
            
            if len(values) < 2:
                raise ValueError("时间序列数据不足，至少需要2个数据点")
            
            # 创建时间序列对象
            ts_data = TimeSeriesData(
                timestamps=timestamps,
                values=values,
                column_name=value_column
            )
            
            # 获取趋势
            trend_direction = ts_data.get_trend()
            
            # 计算趋势强度（基于线性回归的R²）
            trend_strength = self._calculate_trend_strength(values)
            
            # 检测异常值
            anomaly_indices = ts_data.detect_anomalies()
            anomalies = [
                {
                    "index": idx,
                    "timestamp": timestamps[idx].isoformat() if isinstance(timestamps[idx], datetime) else str(timestamps[idx]),
                    "value": values[idx],
                    "deviation": abs(values[idx] - statistics.mean(values)) / statistics.stdev(values) if len(values) > 1 else 0
                }
                for idx in anomaly_indices
            ]
            
            # 简单预测（基于移动平均）
            predictions = self._predict_next_values(values, predict_steps)
            
            # 生成洞察
            insights = []
            insights.append(f"数据趋势：{self._translate_trend(trend_direction)}，趋势强度：{trend_strength:.2f}")
            
            if anomalies:
                insights.append(f"检测到{len(anomalies)}个异常值")
            
            if trend_direction == "increasing":
                insights.append(f"数值呈上升趋势，平均增长率约{self._calculate_growth_rate(values):.1f}%")
            elif trend_direction == "decreasing":
                insights.append(f"数值呈下降趋势，平均下降率约{abs(self._calculate_growth_rate(values)):.1f}%")
            
            return TrendAnalysisResult(
                analysis_id=f"trend_{datetime.now().timestamp()}",
                column_name=value_column,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                anomalies=anomalies,
                predictions=predictions,
                insights=insights,
                created_at=datetime.now()
            )
            
        except Exception as e:
            raise Exception(f"时间序列分析失败: {str(e)}")
    
    async def compare_results_detailed(
        self,
        current_result: QueryResult,
        previous_result: QueryResult
    ) -> ComparisonResult:
        """
        详细对比两个查询结果
        
        Args:
            current_result: 当前查询结果
            previous_result: 之前的查询结果
            
        Returns:
            对比结果
        """
        try:
            # 生成数据摘要
            current_summary = self._generate_data_summary(current_result)
            previous_summary = self._generate_data_summary(previous_result)
            
            # 计算差异
            differences = []
            
            # 行数变化
            row_diff = current_result.row_count - previous_result.row_count
            if row_diff != 0:
                differences.append({
                    "type": "row_count",
                    "description": f"行数变化：{previous_result.row_count} → {current_result.row_count}",
                    "change": row_diff,
                    "change_percent": (row_diff / previous_result.row_count * 100) if previous_result.row_count > 0 else 0
                })
            
            # 数值列的变化
            common_columns = set(current_result.columns) & set(previous_result.columns)
            for col in common_columns:
                current_values = [row.get(col) for row in current_result.data if isinstance(row.get(col), (int, float))]
                previous_values = [row.get(col) for row in previous_result.data if isinstance(row.get(col), (int, float))]
                
                if current_values and previous_values:
                    current_avg = statistics.mean(current_values)
                    previous_avg = statistics.mean(previous_values)
                    
                    if abs(current_avg - previous_avg) > 0.01:
                        diff_percent = ((current_avg - previous_avg) / previous_avg * 100) if previous_avg != 0 else 0
                        differences.append({
                            "type": "column_average",
                            "column": col,
                            "description": f"列 {col} 平均值变化：{previous_avg:.2f} → {current_avg:.2f}",
                            "change": current_avg - previous_avg,
                            "change_percent": diff_percent
                        })
            
            # 生成洞察
            insights = []
            
            if row_diff > 0:
                insights.append(f"数据量增加了{row_diff}行（{row_diff/previous_result.row_count*100:.1f}%）")
            elif row_diff < 0:
                insights.append(f"数据量减少了{abs(row_diff)}行（{abs(row_diff)/previous_result.row_count*100:.1f}%）")
            
            for diff in differences:
                if diff["type"] == "column_average" and abs(diff["change_percent"]) > 10:
                    direction = "增加" if diff["change_percent"] > 0 else "减少"
                    insights.append(f"列 {diff['column']} 的平均值{direction}了{abs(diff['change_percent']):.1f}%")
            
            return ComparisonResult(
                comparison_id=f"comparison_{datetime.now().timestamp()}",
                current_summary=current_summary,
                previous_summary=previous_summary,
                differences=differences,
                insights=insights,
                created_at=datetime.now()
            )
            
        except Exception as e:
            raise Exception(f"数据对比失败: {str(e)}")
    
    async def detect_anomalies(
        self,
        result: QueryResult,
        column_name: str,
        threshold: float = 2.0
    ) -> Dict[str, Any]:
        """
        检测数据异常
        
        Args:
            result: 查询结果
            column_name: 要检测的列名
            threshold: 异常阈值（标准差倍数）
            
        Returns:
            异常检测结果
        """
        try:
            # 提取数值
            values = []
            for row in result.data:
                if column_name in row:
                    try:
                        value = float(row[column_name])
                        values.append(value)
                    except:
                        continue
            
            if len(values) < 3:
                return {
                    "column": column_name,
                    "anomalies": [],
                    "message": "数据点不足，无法进行异常检测"
                }
            
            # 计算统计量
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            # 检测异常
            anomalies = []
            for i, value in enumerate(values):
                z_score = abs(value - mean) / stdev if stdev > 0 else 0
                if z_score > threshold:
                    anomalies.append({
                        "index": i,
                        "value": value,
                        "z_score": z_score,
                        "deviation": value - mean
                    })
            
            return {
                "column": column_name,
                "total_values": len(values),
                "mean": mean,
                "stdev": stdev,
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "anomaly_rate": len(anomalies) / len(values) * 100
            }
            
        except Exception as e:
            raise Exception(f"异常检测失败: {str(e)}")
    
    async def multi_dimensional_analysis(
        self,
        result: QueryResult,
        dimensions: List[str],
        metric: str
    ) -> Dict[str, Any]:
        """
        多维度数据分析
        
        Args:
            result: 查询结果
            dimensions: 维度列名列表
            metric: 指标列名
            
        Returns:
            多维度分析结果
        """
        try:
            # 按维度分组
            groups = {}
            for row in result.data:
                # 构建分组键
                key_parts = []
                for dim in dimensions:
                    if dim in row:
                        key_parts.append(str(row[dim]))
                
                if not key_parts:
                    continue
                
                key = tuple(key_parts)
                
                # 提取指标值
                if metric in row:
                    try:
                        value = float(row[metric])
                        if key not in groups:
                            groups[key] = []
                        groups[key].append(value)
                    except:
                        continue
            
            # 计算每个分组的统计量
            analysis_results = []
            for key, values in groups.items():
                if values:
                    analysis_results.append({
                        "dimensions": dict(zip(dimensions, key)),
                        "count": len(values),
                        "sum": sum(values),
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "min": min(values),
                        "max": max(values),
                        "stdev": statistics.stdev(values) if len(values) > 1 else 0
                    })
            
            # 排序（按平均值降序）
            analysis_results.sort(key=lambda x: x["mean"], reverse=True)
            
            # 生成洞察
            insights = []
            if analysis_results:
                top_group = analysis_results[0]
                insights.append(f"最高平均值组合：{top_group['dimensions']}，平均值：{top_group['mean']:.2f}")
                
                if len(analysis_results) > 1:
                    bottom_group = analysis_results[-1]
                    insights.append(f"最低平均值组合：{bottom_group['dimensions']}，平均值：{bottom_group['mean']:.2f}")
                    
                    diff_percent = (top_group['mean'] - bottom_group['mean']) / bottom_group['mean'] * 100 if bottom_group['mean'] != 0 else 0
                    insights.append(f"最高与最低相差{diff_percent:.1f}%")
            
            return {
                "dimensions": dimensions,
                "metric": metric,
                "group_count": len(analysis_results),
                "groups": analysis_results,
                "insights": insights
            }
            
        except Exception as e:
            raise Exception(f"多维度分析失败: {str(e)}")
    
    def _generate_data_summary(self, result: QueryResult) -> Dict[str, Any]:
        """生成数据摘要"""
        summary = {
            "row_count": result.row_count,
            "column_count": len(result.columns),
            "columns": result.columns
        }
        
        # 计算数值列的统计量
        numeric_stats = {}
        for col in result.columns:
            values = [row.get(col) for row in result.data if isinstance(row.get(col), (int, float))]
            if values:
                numeric_stats[col] = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "stdev": statistics.stdev(values) if len(values) > 1 else 0
                }
        
        summary["numeric_stats"] = numeric_stats
        return summary
    
    def _calculate_trend_strength(self, values: List[float]) -> float:
        """计算趋势强度（简化的R²）"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        
        # 计算线性回归
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator_x = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator_x == 0:
            return 0.0
        
        # 计算R²
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        if ss_tot == 0:
            return 0.0
        
        slope = numerator / denominator_x
        predictions = [y_mean + slope * (x[i] - x_mean) for i in range(n)]
        ss_res = sum((values[i] - predictions[i]) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot)
        return max(0.0, min(1.0, r_squared))
    
    def _predict_next_values(self, values: List[float], steps: int) -> List[Dict[str, Any]]:
        """简单预测（移动平均）"""
        if len(values) < 3:
            return []
        
        # 使用最后3个值的平均值作为预测
        window_size = min(3, len(values))
        last_values = values[-window_size:]
        predicted_value = statistics.mean(last_values)
        
        predictions = []
        for i in range(steps):
            predictions.append({
                "step": i + 1,
                "predicted_value": predicted_value,
                "confidence": "low"  # 简单预测，置信度较低
            })
        
        return predictions
    
    def _calculate_growth_rate(self, values: List[float]) -> float:
        """计算平均增长率"""
        if len(values) < 2:
            return 0.0
        
        first_half_avg = statistics.mean(values[:len(values)//2])
        second_half_avg = statistics.mean(values[len(values)//2:])
        
        if first_half_avg == 0:
            return 0.0
        
        return (second_half_avg - first_half_avg) / first_half_avg * 100
    
    def _translate_trend(self, trend: str) -> str:
        """翻译趋势方向"""
        translations = {
            "increasing": "上升",
            "decreasing": "下降",
            "stable": "稳定",
            "insufficient_data": "数据不足"
        }
        return translations.get(trend, trend)

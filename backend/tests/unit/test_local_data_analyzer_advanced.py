"""
本地数据分析引擎高级功能单元测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import statistics

from src.services.local_data_analyzer import (
    LocalDataAnalyzer,
    QueryResult,
    TimeSeriesData,
    ComparisonResult,
    TrendAnalysisResult
)


@pytest.fixture
def analyzer():
    """创建分析器实例"""
    return LocalDataAnalyzer(
        openai_api_key="test-key",
        openai_base_url="http://localhost:11434/v1",
        model_name="qwen2.5:latest"
    )


@pytest.fixture
def time_series_result():
    """创建时间序列查询结果"""
    base_time = datetime(2024, 1, 1)
    data = [
        {
            "date": (base_time + timedelta(days=i)).isoformat(),
            "value": 100 + i * 10 + (5 if i % 3 == 0 else 0)  # 上升趋势 + 小波动
        }
        for i in range(10)
    ]
    
    return QueryResult(
        query_id="ts_001",
        sql="SELECT date, value FROM metrics",
        data=data,
        columns=["date", "value"],
        row_count=len(data),
        executed_at=datetime.now()
    )


@pytest.fixture
def comparison_results():
    """创建用于对比的查询结果"""
    current = QueryResult(
        query_id="current_001",
        sql="SELECT * FROM sales",
        data=[
            {"product": "A", "sales": 150},
            {"product": "B", "sales": 200},
            {"product": "C", "sales": 180}
        ],
        columns=["product", "sales"],
        row_count=3,
        executed_at=datetime.now()
    )
    
    previous = QueryResult(
        query_id="previous_001",
        sql="SELECT * FROM sales",
        data=[
            {"product": "A", "sales": 100},
            {"product": "B", "sales": 150}
        ],
        columns=["product", "sales"],
        row_count=2,
        executed_at=datetime.now() - timedelta(days=1)
    )
    
    return current, previous


class TestTimeSeriesData:
    """测试时间序列数据类"""
    
    def test_get_trend_increasing(self):
        """测试上升趋势检测"""
        ts = TimeSeriesData(
            timestamps=[datetime.now() for _ in range(5)],
            values=[10, 15, 20, 25, 30],
            column_name="value"
        )
        
        assert ts.get_trend() == "increasing"
    
    def test_get_trend_decreasing(self):
        """测试下降趋势检测"""
        ts = TimeSeriesData(
            timestamps=[datetime.now() for _ in range(5)],
            values=[30, 25, 20, 15, 10],
            column_name="value"
        )
        
        assert ts.get_trend() == "decreasing"
    
    def test_get_trend_stable(self):
        """测试稳定趋势检测"""
        ts = TimeSeriesData(
            timestamps=[datetime.now() for _ in range(5)],
            values=[20, 21, 20, 19, 20],
            column_name="value"
        )
        
        assert ts.get_trend() == "stable"
    
    def test_detect_anomalies(self):
        """测试异常值检测"""
        ts = TimeSeriesData(
            timestamps=[datetime.now() for _ in range(6)],
            values=[10, 12, 11, 50, 13, 12],  # 50是异常值
            column_name="value"
        )
        
        anomalies = ts.detect_anomalies(threshold=2.0)
        assert len(anomalies) > 0
        assert 3 in anomalies  # 索引3的值50是异常值
    
    def test_detect_anomalies_insufficient_data(self):
        """测试数据不足时的异常检测"""
        ts = TimeSeriesData(
            timestamps=[datetime.now(), datetime.now()],
            values=[10, 12],
            column_name="value"
        )
        
        anomalies = ts.detect_anomalies()
        assert len(anomalies) == 0


class TestTimeSeriesAnalysis:
    """测试时间序列分析"""
    
    @pytest.mark.asyncio
    async def test_analyze_time_series_success(self, analyzer, time_series_result):
        """测试时间序列分析成功"""
        result = await analyzer.analyze_time_series(
            result=time_series_result,
            time_column="date",
            value_column="value",
            predict_steps=3
        )
        
        assert isinstance(result, TrendAnalysisResult)
        assert result.column_name == "value"
        assert result.trend_direction in ["increasing", "decreasing", "stable"]
        assert 0 <= result.trend_strength <= 1
        assert len(result.predictions) == 3
        assert len(result.insights) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_time_series_insufficient_data(self, analyzer):
        """测试数据不足时的时间序列分析"""
        result = QueryResult(
            query_id="ts_002",
            sql="SELECT date, value FROM metrics",
            data=[{"date": datetime.now().isoformat(), "value": 100}],
            columns=["date", "value"],
            row_count=1,
            executed_at=datetime.now()
        )
        
        with pytest.raises(Exception, match="时间序列数据不足"):
            await analyzer.analyze_time_series(
                result=result,
                time_column="date",
                value_column="value"
            )
    
    @pytest.mark.asyncio
    async def test_analyze_time_series_invalid_column(self, analyzer, time_series_result):
        """测试无效列名的时间序列分析"""
        with pytest.raises(Exception):
            await analyzer.analyze_time_series(
                result=time_series_result,
                time_column="invalid_column",
                value_column="value"
            )


class TestDataComparison:
    """测试数据对比"""
    
    @pytest.mark.asyncio
    async def test_compare_results_detailed_success(self, analyzer, comparison_results):
        """测试详细对比成功"""
        current, previous = comparison_results
        
        result = await analyzer.compare_results_detailed(
            current_result=current,
            previous_result=previous
        )
        
        assert isinstance(result, ComparisonResult)
        assert result.current_summary["row_count"] == 3
        assert result.previous_summary["row_count"] == 2
        assert len(result.differences) > 0
        assert len(result.insights) > 0
    
    @pytest.mark.asyncio
    async def test_compare_results_row_count_change(self, analyzer, comparison_results):
        """测试行数变化检测"""
        current, previous = comparison_results
        
        result = await analyzer.compare_results_detailed(
            current_result=current,
            previous_result=previous
        )
        
        # 检查是否检测到行数变化
        row_diff = [d for d in result.differences if d["type"] == "row_count"]
        assert len(row_diff) > 0
        assert row_diff[0]["change"] == 1  # 3 - 2 = 1
    
    @pytest.mark.asyncio
    async def test_compare_results_column_average_change(self, analyzer, comparison_results):
        """测试列平均值变化检测"""
        current, previous = comparison_results
        
        result = await analyzer.compare_results_detailed(
            current_result=current,
            previous_result=previous
        )
        
        # 检查是否检测到平均值变化
        avg_diff = [d for d in result.differences if d["type"] == "column_average"]
        assert len(avg_diff) > 0


class TestAnomalyDetection:
    """测试异常检测"""
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self, analyzer):
        """测试异常检测成功"""
        result = QueryResult(
            query_id="anomaly_001",
            sql="SELECT value FROM data",
            data=[
                {"value": 10},
                {"value": 12},
                {"value": 11},
                {"value": 50},  # 异常值
                {"value": 13},
                {"value": 12}
            ],
            columns=["value"],
            row_count=6,
            executed_at=datetime.now()
        )
        
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name="value",
            threshold=2.0
        )
        
        assert anomaly_result["column"] == "value"
        assert anomaly_result["total_values"] == 6
        assert anomaly_result["anomaly_count"] > 0
        assert len(anomaly_result["anomalies"]) > 0
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(self, analyzer):
        """测试数据不足时的异常检测"""
        result = QueryResult(
            query_id="anomaly_002",
            sql="SELECT value FROM data",
            data=[{"value": 10}, {"value": 12}],
            columns=["value"],
            row_count=2,
            executed_at=datetime.now()
        )
        
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name="value"
        )
        
        assert anomaly_result["anomalies"] == []
        assert "数据点不足" in anomaly_result["message"]
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_no_anomalies(self, analyzer):
        """测试无异常值的情况"""
        result = QueryResult(
            query_id="anomaly_003",
            sql="SELECT value FROM data",
            data=[{"value": i} for i in range(10, 20)],
            columns=["value"],
            row_count=10,
            executed_at=datetime.now()
        )
        
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name="value",
            threshold=2.0
        )
        
        assert anomaly_result["anomaly_count"] == 0


class TestMultiDimensionalAnalysis:
    """测试多维度分析"""
    
    @pytest.mark.asyncio
    async def test_multi_dimensional_analysis_success(self, analyzer):
        """测试多维度分析成功"""
        result = QueryResult(
            query_id="multi_001",
            sql="SELECT region, product, sales FROM data",
            data=[
                {"region": "North", "product": "A", "sales": 100},
                {"region": "North", "product": "B", "sales": 150},
                {"region": "South", "product": "A", "sales": 120},
                {"region": "South", "product": "B", "sales": 180},
            ],
            columns=["region", "product", "sales"],
            row_count=4,
            executed_at=datetime.now()
        )
        
        analysis_result = await analyzer.multi_dimensional_analysis(
            result=result,
            dimensions=["region", "product"],
            metric="sales"
        )
        
        assert analysis_result["dimensions"] == ["region", "product"]
        assert analysis_result["metric"] == "sales"
        assert analysis_result["group_count"] == 4
        assert len(analysis_result["groups"]) == 4
        assert len(analysis_result["insights"]) > 0
    
    @pytest.mark.asyncio
    async def test_multi_dimensional_analysis_single_dimension(self, analyzer):
        """测试单维度分析"""
        result = QueryResult(
            query_id="multi_002",
            sql="SELECT region, sales FROM data",
            data=[
                {"region": "North", "sales": 100},
                {"region": "North", "sales": 150},
                {"region": "South", "sales": 120},
            ],
            columns=["region", "sales"],
            row_count=3,
            executed_at=datetime.now()
        )
        
        analysis_result = await analyzer.multi_dimensional_analysis(
            result=result,
            dimensions=["region"],
            metric="sales"
        )
        
        assert analysis_result["group_count"] == 2  # North and South
        
        # 检查统计量
        for group in analysis_result["groups"]:
            assert "mean" in group
            assert "median" in group
            assert "min" in group
            assert "max" in group
    
    @pytest.mark.asyncio
    async def test_multi_dimensional_analysis_sorting(self, analyzer):
        """测试多维度分析结果排序"""
        result = QueryResult(
            query_id="multi_003",
            sql="SELECT category, value FROM data",
            data=[
                {"category": "A", "value": 50},
                {"category": "B", "value": 200},
                {"category": "C", "value": 100},
            ],
            columns=["category", "value"],
            row_count=3,
            executed_at=datetime.now()
        )
        
        analysis_result = await analyzer.multi_dimensional_analysis(
            result=result,
            dimensions=["category"],
            metric="value"
        )
        
        # 结果应该按平均值降序排列
        groups = analysis_result["groups"]
        assert groups[0]["mean"] >= groups[1]["mean"]
        assert groups[1]["mean"] >= groups[2]["mean"]


class TestHelperMethods:
    """测试辅助方法"""
    
    def test_calculate_trend_strength(self, analyzer):
        """测试趋势强度计算"""
        # 强上升趋势
        strong_trend = [10, 20, 30, 40, 50]
        strength = analyzer._calculate_trend_strength(strong_trend)
        assert strength > 0.9
        
        # 弱趋势
        weak_trend = [10, 12, 11, 13, 12]
        strength = analyzer._calculate_trend_strength(weak_trend)
        assert strength < 0.5
    
    def test_predict_next_values(self, analyzer):
        """测试预测功能"""
        values = [10, 12, 14, 16, 18]
        predictions = analyzer._predict_next_values(values, steps=3)
        
        assert len(predictions) == 3
        for pred in predictions:
            assert "step" in pred
            assert "predicted_value" in pred
            assert "confidence" in pred
    
    def test_calculate_growth_rate(self, analyzer):
        """测试增长率计算"""
        # 增长情况
        growing = [10, 12, 14, 16, 18]
        rate = analyzer._calculate_growth_rate(growing)
        assert rate > 0
        
        # 下降情况
        declining = [18, 16, 14, 12, 10]
        rate = analyzer._calculate_growth_rate(declining)
        assert rate < 0
    
    def test_translate_trend(self, analyzer):
        """测试趋势翻译"""
        assert analyzer._translate_trend("increasing") == "上升"
        assert analyzer._translate_trend("decreasing") == "下降"
        assert analyzer._translate_trend("stable") == "稳定"
        assert analyzer._translate_trend("insufficient_data") == "数据不足"
    
    def test_generate_data_summary(self, analyzer):
        """测试数据摘要生成"""
        result = QueryResult(
            query_id="summary_001",
            sql="SELECT * FROM data",
            data=[
                {"id": 1, "value": 100},
                {"id": 2, "value": 150},
                {"id": 3, "value": 120}
            ],
            columns=["id", "value"],
            row_count=3,
            executed_at=datetime.now()
        )
        
        summary = analyzer._generate_data_summary(result)
        
        assert summary["row_count"] == 3
        assert summary["column_count"] == 2
        assert "numeric_stats" in summary
        assert "value" in summary["numeric_stats"]
        assert "mean" in summary["numeric_stats"]["value"]


class TestEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_empty_data(self, analyzer):
        """测试空数据"""
        result = QueryResult(
            query_id="empty_001",
            sql="SELECT * FROM data",
            data=[],
            columns=["value"],
            row_count=0,
            executed_at=datetime.now()
        )
        
        # 异常检测应该处理空数据
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name="value"
        )
        assert anomaly_result["anomalies"] == []
    
    @pytest.mark.asyncio
    async def test_single_value(self, analyzer):
        """测试单个数值"""
        result = QueryResult(
            query_id="single_001",
            sql="SELECT value FROM data",
            data=[{"value": 100}],
            columns=["value"],
            row_count=1,
            executed_at=datetime.now()
        )
        
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name="value"
        )
        assert "数据点不足" in anomaly_result["message"]
    
    @pytest.mark.asyncio
    async def test_non_numeric_values(self, analyzer):
        """测试非数值数据"""
        result = QueryResult(
            query_id="non_numeric_001",
            sql="SELECT name FROM data",
            data=[
                {"name": "Alice"},
                {"name": "Bob"},
                {"name": "Charlie"}
            ],
            columns=["name"],
            row_count=3,
            executed_at=datetime.now()
        )
        
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name="name"
        )
        assert "数据点不足" in anomaly_result["message"]

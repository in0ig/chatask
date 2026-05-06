#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Few-Shot样本管理工具
用于管理、验证和优化Few-Shot样本库
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.services.few_shot_sample_manager import (
    EnhancedFewShotManager,
    SampleType,
    SampleStatus
)


def list_samples(manager: EnhancedFewShotManager, prompt_type: str = None):
    """列出样本"""
    print("=" * 60)
    print("Few-Shot 样本库统计")
    print("=" * 60)
    
    stats = manager.get_sample_statistics(prompt_type)
    
    print(f"总样本数: {stats['total_samples']}")
    print(f"状态分布: {stats['status_distribution']}")
    print(f"类型分布: {stats['type_distribution']}")
    
    if stats['quality_metrics']:
        print("\n质量指标:")
        metrics = stats['quality_metrics']
        print(f"  平均验证分数: {metrics['avg_validation_score']:.2f}")
        print(f"  平均成功率: {metrics['avg_success_rate']:.2f}")
        print(f"  平均用户反馈: {metrics['avg_user_feedback']:.2f}")
        print(f"  有使用记录的样本: {metrics['samples_with_usage']}")
        print(f"  有用户反馈的样本: {metrics['samples_with_feedback']}")
    
    if stats['recent_activity']:
        print("\n最近活动:")
        activity = stats['recent_activity']
        print(f"  上周新增样本: {activity['samples_added_last_week']}")
        print(f"  上周使用样本: {activity['samples_used_last_week']}")
    
    # 详细列出样本
    if prompt_type:
        samples = manager.samples.get(prompt_type, [])
    else:
        samples = [sample for sample_list in manager.samples.values() for sample in sample_list]
    
    if samples:
        print(f"\n样本详情 (共 {len(samples)} 个):")
        print("-" * 60)
        for i, sample in enumerate(samples[:10]):  # 只显示前10个
            print(f"{i+1}. [{sample.sample_id}] {sample.prompt_type}")
            print(f"   输入: {sample.input_text[:50]}...")
            print(f"   状态: {sample.status.value} | 类型: {sample.sample_type.value}")
            print(f"   使用次数: {sample.metrics.usage_count} | 成功率: {sample.metrics.success_rate:.2f}")
            print()
        
        if len(samples) > 10:
            print(f"... 还有 {len(samples) - 10} 个样本")


def add_sample(manager: EnhancedFewShotManager, prompt_type: str, input_text: str, 
               output_text: str, sample_type: str = "positive", description: str = ""):
    """添加新样本"""
    print(f"添加新样本到 {prompt_type}...")
    
    sample_type_enum = SampleType(sample_type)
    
    success, errors = manager.add_sample(
        prompt_type=prompt_type,
        input_text=input_text,
        output_text=output_text,
        sample_type=sample_type_enum,
        description=description,
        created_by="admin"
    )
    
    if success:
        print("✅ 样本添加成功!")
        if errors:
            print(f"⚠️  警告: {'; '.join(errors)}")
    else:
        print("❌ 样本添加失败:")
        for error in errors:
            print(f"   - {error}")


def validate_samples(manager: EnhancedFewShotManager):
    """验证所有样本"""
    print("验证样本库...")
    
    total_samples = 0
    valid_samples = 0
    invalid_samples = 0
    
    for prompt_type, samples in manager.samples.items():
        print(f"\n验证 {prompt_type} 类型样本:")
        
        for sample in samples:
            total_samples += 1
            is_valid, errors = manager.validator.validate_sample(sample)
            
            if is_valid:
                valid_samples += 1
                print(f"  ✅ {sample.sample_id}: 有效")
            else:
                invalid_samples += 1
                print(f"  ❌ {sample.sample_id}: 无效")
                for error in errors:
                    print(f"     - {error}")
    
    print(f"\n验证结果:")
    print(f"  总样本数: {total_samples}")
    print(f"  有效样本: {valid_samples}")
    print(f"  无效样本: {invalid_samples}")
    print(f"  有效率: {valid_samples/total_samples*100:.1f}%" if total_samples > 0 else "  有效率: 0%")


def cleanup_samples(manager: EnhancedFewShotManager, min_validation_score: float = 0.5,
                   min_success_rate: float = 0.3, min_usage_count: int = 5):
    """清理低质量样本"""
    print(f"清理低质量样本...")
    print(f"  最低验证分数: {min_validation_score}")
    print(f"  最低成功率: {min_success_rate}")
    print(f"  最低使用次数: {min_usage_count}")
    
    removed_count = manager.cleanup_low_quality_samples(
        min_validation_score=min_validation_score,
        min_success_rate=min_success_rate,
        min_usage_count=min_usage_count
    )
    
    print(f"✅ 已清理 {removed_count} 个低质量样本")


def test_similarity(manager: EnhancedFewShotManager, prompt_type: str, query_text: str):
    """测试相似度匹配"""
    print(f"测试相似度匹配:")
    print(f"  查询类型: {prompt_type}")
    print(f"  查询文本: {query_text}")
    
    similar_samples = manager.get_similar_samples(
        prompt_type=prompt_type,
        query_text=query_text,
        max_samples=5,
        min_similarity=0.01  # Lower threshold for testing
    )
    
    if similar_samples:
        print(f"\n找到 {len(similar_samples)} 个相似样本:")
        for i, (sample, similarity) in enumerate(similar_samples):
            print(f"  {i+1}. 相似度: {similarity:.3f}")
            print(f"     样本ID: {sample.sample_id}")
            print(f"     输入: {sample.input_text}")
            print(f"     输出: {sample.output_text[:100]}...")
            print()
    else:
        print("❌ 未找到相似样本")


def export_samples(manager: EnhancedFewShotManager, output_file: str):
    """导出样本到文件"""
    print(f"导出样本到 {output_file}...")
    
    # 这里可以实现导出逻辑，比如导出为CSV或Excel
    stats = manager.get_sample_statistics()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Few-Shot样本库统计报告\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"总样本数: {stats['total_samples']}\n")
        f.write(f"状态分布: {stats['status_distribution']}\n")
        f.write(f"类型分布: {stats['type_distribution']}\n")
        
        if stats['quality_metrics']:
            f.write(f"\n质量指标:\n")
            metrics = stats['quality_metrics']
            f.write(f"  平均验证分数: {metrics['avg_validation_score']:.2f}\n")
            f.write(f"  平均成功率: {metrics['avg_success_rate']:.2f}\n")
            f.write(f"  平均用户反馈: {metrics['avg_user_feedback']:.2f}\n")
    
    print(f"✅ 导出完成: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Few-Shot样本管理工具")
    parser.add_argument("--config", default="backend/config/enhanced_few_shot_samples.json",
                       help="样本配置文件路径")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出样本
    list_parser = subparsers.add_parser("list", help="列出样本")
    list_parser.add_argument("--type", help="指定样本类型")
    
    # 添加样本
    add_parser = subparsers.add_parser("add", help="添加样本")
    add_parser.add_argument("--type", required=True, help="样本类型")
    add_parser.add_argument("--input", required=True, help="输入文本")
    add_parser.add_argument("--output", required=True, help="输出文本")
    add_parser.add_argument("--sample-type", default="positive", 
                           choices=["positive", "negative", "edge_case", "template"],
                           help="样本类型")
    add_parser.add_argument("--description", default="", help="样本描述")
    
    # 验证样本
    validate_parser = subparsers.add_parser("validate", help="验证样本")
    
    # 清理样本
    cleanup_parser = subparsers.add_parser("cleanup", help="清理低质量样本")
    cleanup_parser.add_argument("--min-validation-score", type=float, default=0.5,
                               help="最低验证分数")
    cleanup_parser.add_argument("--min-success-rate", type=float, default=0.3,
                               help="最低成功率")
    cleanup_parser.add_argument("--min-usage-count", type=int, default=5,
                               help="最低使用次数")
    
    # 测试相似度
    similarity_parser = subparsers.add_parser("similarity", help="测试相似度匹配")
    similarity_parser.add_argument("--type", required=True, help="样本类型")
    similarity_parser.add_argument("--query", required=True, help="查询文本")
    
    # 导出样本
    export_parser = subparsers.add_parser("export", help="导出样本统计")
    export_parser.add_argument("--output", required=True, help="输出文件路径")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化管理器
    manager = EnhancedFewShotManager(samples_path=args.config)
    
    # 执行命令
    if args.command == "list":
        list_samples(manager, args.type)
    elif args.command == "add":
        add_sample(manager, args.type, args.input, args.output, 
                  args.sample_type, args.description)
    elif args.command == "validate":
        validate_samples(manager)
    elif args.command == "cleanup":
        cleanup_samples(manager, args.min_validation_score, 
                       args.min_success_rate, args.min_usage_count)
    elif args.command == "similarity":
        test_similarity(manager, args.type, args.query)
    elif args.command == "export":
        export_samples(manager, args.output)


if __name__ == "__main__":
    main()
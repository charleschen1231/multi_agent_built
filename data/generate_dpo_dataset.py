#!/usr/bin/env python3
"""
从 SFT 数据集生成 DPO 偏好对数据集

逻辑：
- chosen: 教师模型的 Ground Truth（优质回答）
- rejected: 基座模型的推理输出（低质回答）
"""
import json
import os
from typing import List, Dict

def generate_dpo_pairs_from_sft(
    sft_dataset_file: str = "data/system_sft_dataset.jsonl",
    output_file: str = "data/dpo_dataset.jsonl"
):
    """
    从 SFT 数据集生成 DPO 偏好对
    
    Args:
        sft_dataset_file: SFT 数据集路径
        output_file: 输出 DPO 数据集路径
    """
    if not os.path.exists(sft_dataset_file):
        print(f"❌ SFT 数据集不存在: {sft_dataset_file}")
        return
    
    # 读取 SFT 数据集
    sft_samples = []
    with open(sft_dataset_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                sft_samples.append(json.loads(line))
    
    print(f"📊 读取到 {len(sft_samples)} 条 SFT 样本")
    
    # 生成 DPO 偏好对
    dpo_pairs = []
    
    for idx, sample in enumerate(sft_samples):
        # 提取用户请求
        user_request = sample.get('input', {}).get('user_request', '')
        if not user_request:
            user_request = sample.get('user_request', '')
        
        # 提取三个 Agent 的 GT
        plan_gt = sample.get('plan_gt', '')
        draft_answer_gt = sample.get('draft_answer_gt', '')
        final_answer_gt = sample.get('final_answer_gt', '')
        
        # 为每个 Agent 生成偏好对
        # Planner: chosen=plan_gt, rejected=模拟的低质规划
        if plan_gt:
            dpo_pairs.append({
                'instruction': f'请为以下问题制定解题计划：{user_request}',
                'input': '',
                'chosen': plan_gt,
                'rejected': f'直接计算 {user_request} 的结果',  # 简化的低质回答
                'metadata': {
                    'agent_id': 'planner',
                    'sample_index': idx,
                    'source': 'sft_dataset'
                }
            })
        
        # Infer: chosen=draft_answer_gt, rejected=模拟的错误推理
        if draft_answer_gt:
            dpo_pairs.append({
                'instruction': f'请解答以下问题：{user_request}',
                'input': '',
                'chosen': draft_answer_gt,
                'rejected': f'答案是错误的，重新计算',  # 简化的低质回答
                'metadata': {
                    'agent_id': 'infer',
                    'sample_index': idx,
                    'source': 'sft_dataset'
                }
            })
        
        # Checker: chosen=final_answer_gt, rejected=模拟的错误检查
        if final_answer_gt:
            dpo_pairs.append({
                'instruction': f'请检查以下答案是否正确：{user_request}',
                'input': '',
                'chosen': final_answer_gt,
                'rejected': f'答案有误，需要修正',  # 简化的低质回答
                'metadata': {
                    'agent_id': 'checker',
                    'sample_index': idx,
                    'source': 'sft_dataset'
                }
            })
    
    print(f"✅ 生成了 {len(dpo_pairs)} 个 DPO 偏好对")
    
    # 保存到文件
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for pair in dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
    
    print(f"💾 DPO 数据集已保存: {output_file}")
    
    # 统计信息
    agent_counts = {}
    for pair in dpo_pairs:
        agent_id = pair['metadata']['agent_id']
        agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
    
    print("\n📈 各 Agent 偏好对数量:")
    for agent_id, count in sorted(agent_counts.items()):
        print(f"  - {agent_id}: {count} 对")


if __name__ == '__main__':
    generate_dpo_pairs_from_sft()

# rollout/recorder.py
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List


class TrajectoryRecorder:
    def __init__(self, output_dir: str = "data/rollouts"):
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(output_dir, f"sft_data_{timestamp}.jsonl")
        print(f"📝 轨迹记录器已初始化，数据将保存至：{self.filepath}")

    def record_step(self, agent_id: str, prompt: str, response: str,
                    ground_truth: Optional[str] = None, metadata: Dict = None):
        """记录单步轨迹（适配蒸馏训练格式）"""
        record = {
            "agent_id": agent_id,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ],
            "meta": metadata or {}
        }

        # 添加 ground_truth（教师模型生成的答案）
        if ground_truth:
            record["ground_truth"] = ground_truth
            # 为 SWIFT 训练添加标准字段
            record["output"] = ground_truth  # SWIFT 期望的字段

        # 添加 loss_weight（用于联合训练）
        if metadata and "loss_weight" in metadata:
            record["loss_weight"] = metadata["loss_weight"]

        # 保存到 JSONL
        with open(self.filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_file_path(self) -> str:
        return self.filepath

    def assemble_sft_dataset(self, output_file: str = None) -> str:
        """
        组装完整的 SFT 训练数据集（按照指南要求）
        将所有 agent 的轨迹合并，每个样本包含所有 GT 字段
        """
        if not output_file:
            output_file = self.filepath.replace(".jsonl", "_sft.jsonl")

        # 读取所有轨迹记录
        with open(self.filepath, 'r', encoding='utf-8') as f:
            records = [json.loads(line) for line in f]

        # 按 sample_id 分组
        samples_dict = {}
        for record in records:
            sample_id = record.get('meta', {}).get('sample_id', 0)
            agent_id = record.get('agent_id')
            
            if sample_id not in samples_dict:
                samples_dict[sample_id] = {
                    'id': sample_id,
                    'user_request': None  # 从 prompt 中提取
                }
            
            # 提取 user_request（从第一个 agent 的 prompt）
            if not samples_dict[sample_id]['user_request'] and record.get('messages'):
                samples_dict[sample_id]['user_request'] = record['messages'][0]['content']
            
            # 添加该 agent 的 ground_truth
            if 'ground_truth' in record:
                gt_key = f"{agent_id}_gt"
                samples_dict[sample_id][gt_key] = record['ground_truth']
            
            # 添加 messages（用于 SFT 训练）
            if 'messages' not in samples_dict[sample_id]:
                samples_dict[sample_id]['messages'] = []
            samples_dict[sample_id]['messages'].append({
                'agent_id': agent_id,
                'prompt': record['messages'][0]['content'],
                'response': record['messages'][1]['content'],
                'ground_truth': record.get('ground_truth')
            })

        # 转换为列表
        sft_dataset = list(samples_dict.values())

        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in sft_dataset:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        print(f"✅ SFT 训练数据集已组装：{output_file} (共 {len(sft_dataset)} 条)")
        return output_file

    def convert_to_swift_format(self, output_file: str = None) -> str:
        """转换为 SWIFT 训练格式（保留完整的 messages）"""
        if not output_file:
            output_file = self.filepath.replace(".jsonl", "_swift.jsonl")

        with open(self.filepath, 'r', encoding='utf-8') as f_in:
            records = [json.loads(line) for line in f_in]

        swift_records = []
        for record in records:
            swift_record = {
                "messages": record["messages"],
                "agent_id": record["agent_id"],
                "loss_weight": record.get("loss_weight", 1.0)
            }
            if "ground_truth" in record:
                swift_record["output"] = record["ground_truth"]
            swift_records.append(swift_record)

        with open(output_file, 'w', encoding='utf-8') as f_out:
            for record in swift_records:
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"✅ SWIFT 格式数据已保存至：{output_file} (共 {len(swift_records)} 条)")

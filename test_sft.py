#!/usr/bin/env python
"""测试 SFT 训练"""
import torch
print(f'CUDA available: {torch.cuda.is_available()}')

from training.sft_trainer import SFTTrainer
trainer = SFTTrainer()

# 测试命令构建 - 使用转换后的数据
result = trainer.train_with_api(
    data_file='test_sft_dataset_swift.jsonl',  # 使用 ms-swift 格式的数据
    model_path='Qwen/Qwen2.5-0.5B-Instruct',
    output_dir='./test_output_dir',
    hyperparameters={
        'use_flash_attn': True,  # 前端传的 true
        'use_lora': True,
        'num_epochs': 1,
        'batch_size': 2,
        'max_length': 512
    },
    log_callback=lambda x: print(f'[LOG] {x}')
)
print(f'Result: {result}')

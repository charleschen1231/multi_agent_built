#!/usr/bin/env python
"""调试页面训练流程"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from training.sft_trainer import SFTTrainer

def test_page_training():
    """模拟页面上的训练流程"""
    print("=" * 60)
    print("调试页面训练流程")
    print("=" * 60)
    
    # 1. 初始化数据库
    print("\n[1] 初始化数据库...")
    try:
        db = DatabaseManager()
        print("✓ 数据库初始化成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return
    
    # 2. 获取系统配置
    print("\n[2] 获取系统配置...")
    try:
        configs = db.get_all_system_configs(only_valid=True)
        if not configs:
            print("✗ 没有找到有效的系统配置")
            return
        config = configs[0]
        config_id = config.id
        print(f"✓ 找到配置: {config.name} (ID: {config_id})")
    except Exception as e:
        print(f"✗ 获取配置失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 获取生成的数据（轨迹）
    print(f"\n[3] 获取配置 {config_id} 的轨迹数据...")
    try:
        generated_data = db.get_generated_data_by_config(config_id)
        print(f"✓ 找到 {len(generated_data)} 条生成的数据")
        
        # 转换为 trajectories 格式
        trajectories = []
        for data in generated_data:
            if data.trajectory:
                traj = data.trajectory
                if isinstance(traj, dict) and 'steps' in traj:
                    trajectories.append(traj)
                elif isinstance(traj, list):
                    trajectories.append({
                        'trajectory_id': data.id,
                        'steps': traj
                    })
        
        print(f"✓ 转换后得到 {len(trajectories)} 条轨迹")
        
        # 如果没有轨迹，使用测试数据
        if not trajectories:
            print("⚠ 未找到轨迹数据，使用测试数据")
            trajectories = [{
                'trajectory_id': 'test',
                'sample_id': 'test',
                'steps': [{
                    'prompt': '计算 15 + 27',
                    'ground_truth': '解题计划：\n步骤1：识别数字15和27\n步骤2：个位数相加：5+7=12，进位1\n步骤3：十位数相加：1+2+1=4\n步骤4：组合结果：42\n\n详细解答：\n15 + 27 = 42\n个位：5+7=12，写2进1\n十位：1+2+1=4\n最终结果：42\n\n最终答案：42',
                    'metadata': {'system_prompt': '你是一个数学解题助手。请按照以下步骤解决数学问题：\n1. 理解问题\n2. 制定解题计划\n3. 执行计算\n4. 验证结果\n5. 给出最终答案\n\n请详细展示你的思考过程。'},
                    'agent_id': 'math_agent'
                }]
            }]
    except Exception as e:
        print(f"✗ 获取轨迹失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 准备训练数据
    print("\n[4] 准备训练数据...")
    try:
        trainer = SFTTrainer()
        import time
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        data_file = f"training_outputs/debug_sft_data_{timestamp}.jsonl"
        data_file = trainer.prepare_training_data(trajectories, output_file=data_file)
        print(f"✓ 训练数据已保存: {data_file}")
        
        # 检查文件内容
        with open(data_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            print(f"✓ 数据格式样例: {first_line[:200]}...")
    except Exception as e:
        print(f"✗ 准备训练数据失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. 启动训练
    print("\n[5] 启动训练...")
    try:
        def log_callback(msg):
            print(f"  [LOG] {msg}")
        
        result = trainer.train_with_api(
            data_file=data_file,
            model_path="Qwen/Qwen2.5-0.5B-Instruct",
            hyperparameters={
                'lr': 2e-5,
                'batch_size': 2,
                'num_epochs': 1,
                'max_length': 512,
                'use_lora': True,
                'lora_rank': 8,
                'lora_alpha': 32,
                'gradient_checkpointing': True
            },
            log_callback=log_callback
        )
        
        print(f"\n✓ 训练结果: {result}")
        
    except Exception as e:
        print(f"✗ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    test_page_training()

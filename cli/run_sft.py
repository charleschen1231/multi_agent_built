import argparse
import glob
import os
import sys
import json

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from traning.sft_trainer import run_training
from runtime.executor import SystemExecutor
from spec.system_spec import SystemSpec


def main():
    parser = argparse.ArgumentParser(description="Run distillation-based SFT training (对齐实施指南)")
    parser.add_argument("--spec", type=str, required=True, help="Path to system specification JSON")
    parser.add_argument("--input", type=str, help="Path to input JSONL file (dataset_raw.jsonl)")
    parser.add_argument("--output_dir", type=str, default="./sft_output", help="Output directory for trained model")
    parser.add_argument("--do_train", action="store_true", help="Whether to run training after data collection")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--teacher_only", action="store_true",
                        help="Only use teacher model to generate data (skip student & training)")
    parser.add_argument("--data_file", type=str, help="Path to existing training data file (skip data collection)")

    args = parser.parse_args()

    # 验证参数
    if not args.data_file and not args.input:
        parser.error("Either --input or --data_file must be provided")

    # 1. 加载系统配置
    system_spec = SystemSpec.from_file(args.spec)
    agents = system_spec.agents

    data_file = None

    # 2. 如果指定了已有数据文件，直接使用
    if args.data_file:
        print("\n" + "=" * 60)
        print("📂 使用已有训练数据")
        print("=" * 60)
        print(f"数据文件：{args.data_file}")
        print("=" * 60 + "\n")
        data_file = args.data_file

        # 检查文件是否存在
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"训练数据文件不存在：{data_file}")

    else:
        # 3. 执行数据收集流程（按照指南的自动化流程）
        # 加载输入数据（只包含 user_request）
        inputs = []
        with open(args.input, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    inputs.append(json.loads(line))

        print("\n" + "=" * 60)
        print("🎯 知识蒸馏流程启动（按照 SFT 实施指南）")
        print("=" * 60)
        print(f"教师模型：{agents[0].get_teacher_model_name()}")
        print(f"学生模型：{agents[0].get_model_name()}")
        print(f"输入样本数：{len(inputs)}")
        print("=" * 60 + "\n")

        # Phase 1: 使用教师模型生成 Ground Truth
        executor = SystemExecutor(agents, enable_recording=True)

        # 如果指定了 --teacher_only，只运行 Phase 1
        use_teacher_for_gt = True
        skip_student_phase = args.teacher_only

        results = executor.run_batch(inputs, use_teacher_for_gt=use_teacher_for_gt,
                                     skip_student_phase=skip_student_phase)

        # 转换为 SWIFT 格式
        if executor.recorder:
            data_file = executor.recorder.generate_final_dataset()
        else:
            print("\n⚠️ 未启用轨迹记录器")
            return

    # 4. Phase 2: 联合训练（如果指定了 --do_train）
    if args.do_train:
        if not data_file:
            print("\n❌ 错误：没有可用的训练数据文件")
            return

        print("\n" + "=" * 60)
        print("🚀 Phase 2: 启动联合训练")
        print("=" * 60)

        run_training(
            data_file=data_file,
            model_path=agents[0].get_model_name(),
            output_dir=args.output_dir,
            lr=args.lr,
            batch_size=args.batch_size,
            epochs=args.epochs,
            config_file=args.spec
        )

        print("\n✅ 整个蒸馏流程完成！")
    else:
        if data_file:
            print("\n📝 数据收集完成！如需训练，请添加 --do_train 参数重新运行")
            print(f"   或者直接使用命令：python cli/run_sft.py --data_file {data_file} --do_train")


if __name__ == "__main__":
    main()
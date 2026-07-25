# cli/run_infer.py
import argparse
import json
from runtime.executor import SystemExecutor
from spec.system_spec import SystemSpec  # 现在可以正确导入 SystemSpec


def main():
    parser = argparse.ArgumentParser(description="Run batch inference with multi-agent system")
    parser.add_argument("--spec", type=str, required=True, help="Path to system specification JSON")
    parser.add_argument("--input", type=str, required=True, help="Path to input JSONL file")
    parser.add_argument("--gt", type=str, required=False, help="Path to ground truth JSONL file (optional)")
    args = parser.parse_args()

    # 加载系统配置 (使用 SystemSpec)
    system_spec = SystemSpec.from_file(args.spec)
    agents = system_spec.agents  # 获取 Agent 列表

    # Load input data
    inputs = []
    with open(args.input, 'r') as f:
        for line in f:
            if line.strip():
                inputs.append(json.loads(line))

    # Load ground truth (if provided)
    gt_list = None
    if args.gt:
        gt_list = []
        with open(args.gt, 'r') as f:
            for line in f:
                if line.strip():
                    gt_list.append(json.loads(line))

    # Run inference
    executor = SystemExecutor(agents, enable_recording=True)
    results = executor.run_batch(inputs, gt_list)

    # Output results (for debugging)
    print("\n✅ 推理完成！结果已保存到 state 中")
    for i, result in enumerate(results):
        print(f"Sample {i} result: {result}")


if __name__ == "__main__":
    main()
import os
import json
import sys
import subprocess  # <--- 补充导入：您的代码后面用到了 subprocess.run
from swift import  # <--- 【关键修复】改为 SftArguments
from swift.utils import get_logger

logger = get_logger()

# 检查 swift 是否导入成功
SWIFT_IMPORT_SUCCESS = True


def calculate_joint_loss(losses_dict: dict, weights_dict: dict) -> float:
    """
    计算联合损失：Loss_total = Σ(weight_i * loss_i)
    注意：SWIFT 内部会自动处理多任务 Loss，此函数主要用于日志记录或自定义逻辑
    """
    total_loss = 0.0
    for agent_id, loss in losses_dict.items():
        weight = weights_dict.get(agent_id, 1.0)
        total_loss += weight * loss

    logger.info(f"Joint Loss: {total_loss:.4f} (weights: {weights_dict})")
    return total_loss


def run_training(data_file: str, model_path: str, output_dir: str,
                 lr: float = 2e-5, batch_size: int = 4, epochs: int = 3,
                 config_file: str = None):
    """
    运行系统级联合训练（使用 SWIFT CLI/API）
    """
    # 从配置文件加载 loss weights (仅用于日志或未来扩展，SWIFT 目前主要靠 dataset 混合比例)
    loss_weights = {}
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for agent_cfg in config:
                agent_id = agent_cfg.get("agent_id")
                weight = agent_cfg.get("training", {}).get("loss", {}).get("weight")
                if weight:
                    loss_weights[agent_id] = weight
            logger.info(f"Loss weights from config: {loss_weights}")
        except Exception as e:
            logger.warning(f"Failed to load config file for weights: {e}")

    # 确定 model_type（从模型路径推断）
    model_type = "qwen2_5-0_5b-instruct"  # 默认
    path_lower = model_path.lower()

    if "1.8b" in path_lower or "1_8b" in path_lower:
        model_type = "qwen2_5-1_8b-instruct"
    elif "1.5b" in path_lower or "1_5b" in path_lower:
        model_type = "qwen2_5-1_5b-instruct"  # 注意：Qwen2.5 通常有 0.5, 1.5, 3, 7, 14, 32, 72B。1.8B 可能是 Qwen2 或特定版本，请确认
    elif "0.5b" in path_lower or "0_5b" in path_lower:
        model_type = "qwen2_5-0_5b-instruct"
    elif "7b" in path_lower or "7b-instruct" in path_lower:
        model_type = "qwen2_5-7b-instruct"
    elif "32b" in path_lower or "32b-instruct" in path_lower:
        model_type = "qwen2_5-32b-instruct"
    elif "qwen2.5" in path_lower and "0.5" not in path_lower and "7" not in path_lower:
        # 尝试更通用的匹配，如果上面都没匹配到
        if "3b" in path_lower:
            model_type = "qwen2_5-3b-instruct"
        elif "14b" in path_lower:
            model_type = "qwen2_5-14b-instruct"

    logger.info(f"Using model_type: {model_type}")
    logger.info(f"Training data: {data_file}")
    logger.info(f"Output dir: {output_dir}")

    # 优先使用 Python API
    if SWIFT_IMPORT_SUCCESS:
        logger.info("\n" + "=" * 60)
        logger.info("🚀 使用 SWIFT Python API 启动训练")
        logger.info("=" * 60)

        try:
            # 配置训练参数
            args = SftArguments(
                # --- 模型配置 ---
                model_type=model_type,
                model=model_path,

                # --- 数据集配置 ---
                # 注意：SWIFT 期望 dataset 是列表，如果是本地文件路径，可能需要特殊前缀或直接路径
                # 如果 data_file 是本地 jsonl 路径，SWIFT 通常能自动识别，或者需要设置为 "train.jsonl" 格式
                # 这里假设传入的是绝对路径
                dataset=[data_file],

                # --- 输出配置 ---
                output_dir=output_dir,

                # --- 训练超参 ---
                learning_rate=lr,
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                gradient_accumulation_steps=1,
                save_steps=100,
                logging_steps=10,

                # --- 其他优化 ---
                max_length=2048,
                warmup_ratio=0.1,
                weight_decay=0.01,
                lr_scheduler_type='cosine',
                # 针对笔记本显存优化
                fp16=True,  # 如果显卡支持
                # use_flash_attn=False, # 如果显存紧张或兼容性问题，可关闭
            )

            logger.info(f"训练参数已配置")
            logger.info(f"\n开始训练...")

            # 启动训练
            sft_main(args)

            logger.info("\n✅ System-level joint SFT training completed successfully!")
            return

        except Exception as e:
            logger.error(f"\n❌ Python API 训练失败：{e}")
            logger.info("尝试回退到命令行方式...")
            # 如果 API 失败，可以选择抛出异常或继续尝试命令行，这里选择抛出以便调试
            raise e

    # --- 命令行 fallback 逻辑 (如果 API 方式被禁用或失败) ---
    # 构建 SWIFT 命令行参数
    swift_cmd = [
        "swift", "sft",
        "--model_type", model_type,
        "--model", model_path,
        "--dataset", data_file,
        "--output_dir", output_dir,
        "--learning_rate", str(lr),
        "--num_train_epochs", str(epochs),
        "--per_device_train_batch_size", str(batch_size),
        "--gradient_accumulation_steps", "1",
        "--save_steps", "100",
        "--logging_steps", "10",
        "--max_length", "2048",
        "--warmup_ratio", "0.1",
        "--weight_decay", "0.01",
        "--lr_scheduler_type", "cosine",
    ]

    # 硬件检测
    try:
        import torch
        if not torch.cuda.is_available():
            logger.info("ℹ️  未检测到 GPU，使用 CPU 训练")
            swift_cmd.extend(["--use_cpu", "--torch_dtype", "float32"])
        else:
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"ℹ️  检测到 GPU: {gpu_name}")
            # 笔记本上 Flash Attention 有时会报错，建议默认关闭或根据情况开启
            swift_cmd.extend(["--use_flash_attn", "false"])
    except:
        pass

    logger.info("\n" + "=" * 60)
    logger.info("🚀 启动 SWIFT 训练命令:")
    logger.info(" ".join(swift_cmd))
    logger.info("=" * 60 + "\n")

    # 执行 SWIFT 命令
    try:
        result = subprocess.run(swift_cmd, check=True)
        if result.returncode == 0:
            logger.info("\n✅ System-level joint SFT training completed successfully!")
        else:
            raise RuntimeError(f"SWIFT training failed with return code {result.returncode}")

    except subprocess.CalledProcessError as e:
        logger.error(f"\n❌ Training failed: {e}")
        raise e
    except Exception as e:
        logger.error(f"\n❌ Training failed: {e}")
        raise e


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="训练数据文件路径")
    parser.add_argument("--model", type=str, default="./models/Qwen2.5-0.5B-Instruct", help="学生模型路径")
    parser.add_argument("--output", type=str, default="./sft_output", help="输出目录")
    parser.add_argument("--config", type=str, help="系统配置文件路径")
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=3)

    args = parser.parse_args()

    run_training(
        data_file=args.data,
        model_path=args.model,
        output_dir=args.output,
        lr=args.lr,
        batch_size=args.batch_size,
        epochs=args.epochs,
        config_file=args.config
    )
# runtime/executor.py
import os
from typing import List, Dict, Any, Optional
from spec.system_spec import AgentSpec, load_agent_list
from runtime.agent_runner import AgentRunner
from rollout.recoder import TrajectoryRecorder


class SystemExecutor:
    def __init__(self, agents: List[AgentSpec], enable_recording: bool = True):
        self.agents = {a.agent_id: a for a in agents}
        self.execution_order = [a.agent_id for a in agents]
        self.runners = {a.agent_id: AgentRunner(a) for a in agents}
        self.recorder = TrajectoryRecorder() if enable_recording else None

    def run_batch(self, inputs: List[Dict[str, Any]], ground_truths: Optional[List[Dict]] = None,
                  use_teacher_for_gt: bool = True, skip_student_phase: bool = False) -> List[Dict]:
        """
        两阶段执行（对齐 SFT 实施指南）：
        Phase 1: 使用教师模型生成所有 ground truth（Plan GT, Draft Answer GT, Final Answer GT）
        Phase 2: 使用学生模型执行并记录轨迹（用于 SFT 训练）
        
        Args:
            inputs: 原始输入列表（只包含 user_request）
            ground_truths: 预定义的 ground truth（可选，通常为空由系统自动生成）
            use_teacher_for_gt: 是否使用教师模型生成 GT
            skip_student_phase: 是否跳过学生阶段（仅生成 GT 时使用）
        """
        batch_state = [dict(item) for item in inputs]
        gt_batch = ground_truths or [{} for _ in inputs]

        # ========== Phase 1: Teacher 生成 Ground Truth ==========
        if use_teacher_for_gt:
            print("\n" + "=" * 60)
            print("🎓 Phase 1: 使用教师模型生成 Ground Truth")
            print("=" * 60)

            for agent_id in self.execution_order:
                agent_spec = self.agents[agent_id]
                runner = self.runners[agent_id]

                # 只有配置了教师模型的 agent 才需要生成 GT
                if not agent_spec.teacher_model:
                    print(f"⚠️  Agent {agent_id} 未配置教师模型，跳过 GT 生成")
                    continue

                print(f"\n--- 教师模型生成：{agent_id} ---")

                for i, state in enumerate(batch_state):
                    try:
                        # 使用教师模型生成
                        teacher_response = runner.generate_teacher_response(state)

                        # 将教师模型的输出作为 ground truth 存入 gt_batch
                        out_key = agent_spec.output[0].key
                        gt_key = agent_spec.training.ground_truth.gt_key if agent_spec.training and agent_spec.training.ground_truth else out_key
                        gt_batch[i][gt_key] = teacher_response

                        # 【关键】更新 state，供后续依赖此输出的 agent 使用
                        state[out_key] = teacher_response

                        print(f"[Sample {i}] Teacher GT ({gt_key}): {teacher_response[:50]}...")

                    except Exception as e:
                        print(f"[Sample {i}] Error in teacher generation for {agent_id}: {e}")
                        raise e

            print("\n✅ Phase 1 完成：所有 Ground Truth 已生成")

        # 如果只需要生成 GT，直接返回
        if skip_student_phase:
            print("\n📝 已跳过学生模型执行阶段")
            return batch_state

        # ========== Phase 2: Student 执行并收集训练数据 ==========
        print("\n" + "=" * 60)
        print("📚 Phase 2: 学生模型执行并收集训练数据")
        print("=" * 60)

        # 【关键修改】重置 state（清除 Phase 1 的教师输出，让学生重新生成）
        batch_state = [dict(item) for item in inputs]

        for agent_id in self.execution_order:
            agent_spec = self.agents[agent_id]
            runner = self.runners[agent_id]

            print(f"\n--- 运行 Student Agent: {agent_id} ---")

            for i, state in enumerate(batch_state):
                try:
                    # 获取 loss_weight
                    loss_weight = 1.0
                    if agent_spec.training and agent_spec.training.loss:
                        loss_weight = agent_spec.training.loss.weight

                    # 运行学生模型
                    response, rendered_prompt = runner.run_with_prompt(state, use_teacher=False)

                    # 更新 state
                    out_key = agent_spec.output[0].key
                    state[out_key] = response

                    print(f"[Sample {i}] Student Output ({out_key}): {response[:50]}...")

                    # 记录轨迹（包含 teacher 生成的 GT）
                    if self.recorder:
                        gt_value = gt_batch[i].get(
                            agent_spec.training.ground_truth.gt_key
                        ) if agent_spec.training and agent_spec.training.ground_truth else None

                        self.recorder.record_step(
                            agent_id=agent_id,
                            prompt=rendered_prompt,
                            response=response,
                            ground_truth=gt_value,
                            metadata={
                                "sample_id": i,
                                "model": agent_spec.get_model_name(),
                                "teacher_model": agent_spec.get_teacher_model_name(),
                                "loss_weight": loss_weight,
                                "phase": "distillation"
                            }
                        )

                except Exception as e:
                    print(f"[Sample {i}] Error in {agent_id}: {e}")
                    raise e

        if self.recorder:
            print(f"\n✅ 执行完成！训练数据已保存至：{self.recorder.get_file_path()}")

        return batch_state
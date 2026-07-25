# evaluation/evaluator.py
"""
System-Level 蒸馏效果评估器

Phase 3 of the distillation pipeline:
Run student pipeline on same dataset, compare per-agent outputs vs teacher trajectories.
Compute metrics: exact match rate, token F1, ROUGE-L, trajectory consistency.
"""
import os
import json
import re
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime


class SystemEvaluator:
    """
    Multi-Agent System 蒸馏效果评估器。
    
    用于比较 student model 输出和 teacher model (GPT-4o) 的 ground truth，
    评估蒸馏后的效果。
    """
    
    def __init__(self, output_dir: str = "./evaluation_outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    # ============== Per-Agent Evaluation ==============
    
    def evaluate_agent(
        self,
        agent_id: str,
        student_outputs: List[str],
        teacher_outputs: List[str],
        log_callback: callable = None
    ) -> Dict[str, Any]:
        """
        评估单个 Agent 的蒸馏效果。
        
        Args:
            agent_id: Agent 标识
            student_outputs: 学生模型的输出列表
            teacher_outputs: 教师模型的输出列表 (ground truth)
            log_callback: 日志回调
        
        Returns:
            Dict: 评估结果
        """
        if len(student_outputs) != len(teacher_outputs):
            raise ValueError(
                f"Agent '{agent_id}': student_outputs ({len(student_outputs)}) "
                f"和 teacher_outputs ({len(teacher_outputs)}) 数量不匹配"
            )
        
        n = len(student_outputs)
        if n == 0:
            return {
                'agent_id': agent_id,
                'sample_count': 0,
                'metrics': {},
                'status': 'error',
                'message': '没有可评估的样本'
            }
        
        # Compute metrics per sample
        exact_matches = 0
        f1_scores = []
        rouge_l_scores = []
        char_overlap_scores = []
        length_ratios = []
        
        for i in range(n):
            student = str(student_outputs[i]).strip() if student_outputs[i] else ''
            teacher = str(teacher_outputs[i]).strip() if teacher_outputs[i] else ''
            
            # Exact match
            if student == teacher:
                exact_matches += 1
            
            # Token F1
            f1 = self._compute_token_f1(student, teacher)
            f1_scores.append(f1)
            
            # ROUGE-L
            rouge_l = self._compute_rouge_l(student, teacher)
            rouge_l_scores.append(rouge_l)
            
            # Character overlap
            char_overlap = self._compute_char_overlap(student, teacher)
            char_overlap_scores.append(char_overlap)
            
            # Length ratio
            if len(teacher) > 0:
                length_ratios.append(min(len(student), len(teacher)) / max(len(student), len(teacher)))
            else:
                length_ratios.append(0.0)
        
        # Aggregate metrics
        exact_match_rate = exact_matches / n
        avg_f1 = sum(f1_scores) / n
        avg_rouge_l = sum(rouge_l_scores) / n
        avg_char_overlap = sum(char_overlap_scores) / n
        avg_length_ratio = sum(length_ratios) / n
        
        # Composite distillation quality score (weighted average)
        quality_score = (
            0.3 * exact_match_rate +
            0.3 * avg_f1 +
            0.2 * avg_rouge_l +
            0.2 * avg_char_overlap
        )
        
        result = {
            'agent_id': agent_id,
            'sample_count': n,
            'metrics': {
                'exact_match_rate': round(exact_match_rate, 4),
                'exact_match_count': exact_matches,
                'avg_token_f1': round(avg_f1, 4),
                'avg_rouge_l': round(avg_rouge_l, 4),
                'avg_char_overlap': round(avg_char_overlap, 4),
                'avg_length_ratio': round(avg_length_ratio, 4),
                'distillation_quality_score': round(quality_score, 4),
            },
            'per_sample': {
                'f1_scores': [round(s, 4) for s in f1_scores],
                'rouge_l_scores': [round(s, 4) for s in rouge_l_scores],
                'exact_matches': [student_outputs[i] == teacher_outputs[i] for i in range(n)]
            },
            'status': 'completed'
        }
        
        if log_callback:
            log_callback(f"[{agent_id}] 评估完成: "
                        f"EM={exact_match_rate:.2%}, F1={avg_f1:.4f}, "
                        f"ROUGE-L={avg_rouge_l:.4f}, Quality={quality_score:.4f}")
        
        return result
    
    # ============== System-Level Evaluation ==============
    
    def evaluate_system(
        self,
        student_trajectories: List[Dict],
        teacher_trajectories: List[Dict],
        config_json: List[Dict] = None,
        log_callback: callable = None
    ) -> Dict[str, Any]:
        """
        System-level 蒸馏效果评估。
        
        比较 student 和 teacher 的完整轨迹，逐 agent 评估。
        
        Args:
            student_trajectories: 学生模型的轨迹列表
                每个元素: {agent_id, messages: [{role, content}], ground_truth, meta}
            teacher_trajectories: 教师模型的轨迹列表（或包含 GT 的数据集）
            config_json: 系统配置（用于确定评估哪些 agent）
            log_callback: 日志回调
        
        Returns:
            Dict: 系统级评估报告
        """
        if log_callback:
            log_callback("=" * 60)
            log_callback("System-Level Distillation Evaluation")
            log_callback("=" * 60)
        
        # Organize data by agent_id
        student_by_agent = {}
        teacher_by_agent = {}
        
        for traj in student_trajectories:
            agent_id = traj.get('agent_id', 'unknown')
            if agent_id not in student_by_agent:
                student_by_agent[agent_id] = []
            
            # Extract student response
            response = ''
            for msg in traj.get('messages', []):
                if msg.get('role') == 'assistant':
                    response = msg.get('content', '')
            student_by_agent[agent_id].append(response)
        
        for traj in teacher_trajectories:
            agent_id = traj.get('agent_id', 'unknown')
            if agent_id not in teacher_by_agent:
                teacher_by_agent[agent_id] = []
            
            # Teacher GT can be in ground_truth field or in messages
            gt = traj.get('ground_truth', '')
            if not gt:
                for msg in traj.get('messages', []):
                    if msg.get('role') == 'assistant':
                        gt = msg.get('content', '')
            teacher_by_agent[agent_id].append(gt)
        
        # Evaluate each agent
        agent_results = []
        all_quality_scores = []
        
        for agent_id in student_by_agent:
            student_outputs = student_by_agent[agent_id]
            teacher_outputs = teacher_by_agent.get(agent_id, [])
            
            if not teacher_outputs:
                if log_callback:
                    log_callback(f"[{agent_id}] ⚠️ 没有 teacher 输出，跳过评估")
                continue
            
            # Align lengths (take minimum)
            min_len = min(len(student_outputs), len(teacher_outputs))
            student_outputs = student_outputs[:min_len]
            teacher_outputs = teacher_outputs[:min_len]
            
            result = self.evaluate_agent(
                agent_id=agent_id,
                student_outputs=student_outputs,
                teacher_outputs=teacher_outputs,
                log_callback=log_callback
            )
            
            agent_results.append(result)
            quality = result.get('metrics', {}).get('distillation_quality_score', 0.0)
            all_quality_scores.append(quality)
        
        # Overall system metrics
        if all_quality_scores:
            overall_quality = sum(all_quality_scores) / len(all_quality_scores)
            best_agent = max(agent_results, key=lambda r: r.get('metrics', {}).get('distillation_quality_score', 0))
            worst_agent = min(agent_results, key=lambda r: r.get('metrics', {}).get('distillation_quality_score', 0))
        else:
            overall_quality = 0.0
            best_agent = None
            worst_agent = None
        
        report = {
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'overall_quality_score': round(overall_quality, 4),
            'agents_evaluated': len(agent_results),
            'agent_results': agent_results,
            'summary': {
                'overall_quality_score': round(overall_quality, 4),
                'best_agent': {
                    'agent_id': best_agent['agent_id'] if best_agent else None,
                    'quality_score': best_agent.get('metrics', {}).get('distillation_quality_score', 0) if best_agent else 0
                },
                'worst_agent': {
                    'agent_id': worst_agent['agent_id'] if worst_agent else None,
                    'quality_score': worst_agent.get('metrics', {}).get('distillation_quality_score', 0) if worst_agent else 0
                },
                'quality_grade': self._compute_quality_grade(overall_quality)
            }
        }
        
        if log_callback:
            log_callback(f"\n{'=' * 60}")
            log_callback(f"System-Level Evaluation Complete")
            log_callback(f"  Overall Quality Score: {overall_quality:.4f}")
            log_callback(f"  Quality Grade: {report['summary']['quality_grade']}")
            log_callback(f"  Agents Evaluated: {len(agent_results)}")
            if best_agent:
                log_callback(f"  Best Agent: {best_agent['agent_id']} "
                           f"({best_agent['metrics']['distillation_quality_score']:.4f})")
            if worst_agent:
                log_callback(f"  Worst Agent: {worst_agent['agent_id']} "
                           f"({worst_agent['metrics']['distillation_quality_score']:.4f})")
            log_callback(f"{'=' * 60}")
        
        return report
    
    def evaluate_from_trajectory_files(
        self,
        student_trajectory_file: str,
        teacher_trajectory_file: str,
        config_json: List[Dict] = None,
        log_callback: callable = None
    ) -> Dict[str, Any]:
        """
        从轨迹文件评估蒸馏效果。
        
        Args:
            student_trajectory_file: 学生模型轨迹 JSONL 文件
            teacher_trajectory_file: 教师模型轨迹 JSONL 文件
            config_json: 系统配置
            log_callback: 日志回调
        
        Returns:
            Dict: 评估报告
        """
        def load_jsonl(filepath):
            records = []
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            return records
        
        student_trajs = load_jsonl(student_trajectory_file)
        teacher_trajs = load_jsonl(teacher_trajectory_file)
        
        if log_callback:
            log_callback(f"Student trajectories: {len(student_trajs)} records")
            log_callback(f"Teacher trajectories: {len(teacher_trajs)} records")
        
        return self.evaluate_system(
            student_trajectories=student_trajs,
            teacher_trajectories=teacher_trajs,
            config_json=config_json,
            log_callback=log_callback
        )
    
    # ============== Trajectory Consistency ==============
    
    def evaluate_trajectory_consistency(
        self,
        student_trajectories: List[Dict],
        teacher_trajectories: List[Dict],
        log_callback: callable = None
    ) -> Dict[str, Any]:
        """
        评估轨迹一致性 — student 和 teacher 在多 agent pipeline 中的
        输出链路是否一致。
        
        检查每个样本的所有 agent 输出链是否和 teacher 的一致。
        """
        # Group by sample_id
        student_by_sample = self._group_by_sample(student_trajectories)
        teacher_by_sample = self._group_by_sample(teacher_trajectories)
        
        consistent_samples = 0
        total_samples = 0
        agent_consistency = {}
        
        for sample_id in student_by_sample:
            if sample_id not in teacher_by_sample:
                continue
            
            total_samples += 1
            student_steps = student_by_sample[sample_id]
            teacher_steps = teacher_by_sample[sample_id]
            
            sample_consistent = True
            for agent_id in student_steps:
                if agent_id not in teacher_steps:
                    sample_consistent = False
                    continue
                
                student_out = student_steps[agent_id]
                teacher_out = teacher_steps[agent_id]
                
                # Check if outputs are close enough
                f1 = self._compute_token_f1(student_out, teacher_out)
                
                if agent_id not in agent_consistency:
                    agent_consistency[agent_id] = []
                agent_consistency[agent_id].append(f1)
                
                if f1 < 0.5:
                    sample_consistent = False
            
            if sample_consistent:
                consistent_samples += 1
        
        consistency_rate = consistent_samples / total_samples if total_samples > 0 else 0.0
        
        # Per-agent average consistency
        avg_agent_consistency = {}
        for agent_id, scores in agent_consistency.items():
            avg_agent_consistency[agent_id] = round(sum(scores) / len(scores), 4) if scores else 0.0
        
        result = {
            'total_samples': total_samples,
            'consistent_samples': consistent_samples,
            'trajectory_consistency_rate': round(consistency_rate, 4),
            'per_agent_consistency': avg_agent_consistency
        }
        
        if log_callback:
            log_callback(f"Trajectory Consistency: {consistency_rate:.2%} "
                        f"({consistent_samples}/{total_samples})")
        
        return result
    
    # ============== Metric Computation Helpers ==============
    
    def _compute_token_f1(self, prediction: str, reference: str) -> float:
        """Token-level F1 score"""
        pred_tokens = prediction.lower().split()
        ref_tokens = reference.lower().split()
        
        if not ref_tokens and not pred_tokens:
            return 1.0
        if not ref_tokens or not pred_tokens:
            return 0.0
        
        pred_counter = Counter(pred_tokens)
        ref_counter = Counter(ref_tokens)
        
        tp = sum((pred_counter & ref_counter).values())
        
        precision = tp / len(pred_tokens) if pred_tokens else 0.0
        recall = tp / len(ref_tokens) if ref_tokens else 0.0
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * precision * recall / (precision + recall)
    
    def _compute_rouge_l(self, prediction: str, reference: str) -> float:
        """ROUGE-L (LCS-based F1)"""
        pred_tokens = prediction.lower().split()
        ref_tokens = reference.lower().split()
        
        if not pred_tokens and not ref_tokens:
            return 1.0
        if not pred_tokens or not ref_tokens:
            return 0.0
        
        m, n = len(ref_tokens), len(pred_tokens)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_tokens[i-1] == pred_tokens[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        
        precision = lcs_length / n if n > 0 else 0.0
        recall = lcs_length / m if m > 0 else 0.0
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * precision * recall / (precision + recall)
    
    def _compute_char_overlap(self, prediction: str, reference: str) -> float:
        """Character-level overlap (Jaccard similarity on character n-grams)"""
        if not prediction and not reference:
            return 1.0
        if not prediction or not reference:
            return 0.0
        
        # Use character bigrams for more nuanced comparison
        def get_bigrams(text):
            text = text.lower().strip()
            return set(text[i:i+2] for i in range(len(text) - 1)) if len(text) > 1 else {text}
        
        pred_bigrams = get_bigrams(prediction)
        ref_bigrams = get_bigrams(reference)
        
        if not pred_bigrams and not ref_bigrams:
            return 1.0
        
        intersection = len(pred_bigrams & ref_bigrams)
        union = len(pred_bigrams | ref_bigrams)
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_quality_grade(self, score: float) -> str:
        """将数值分数转换为质量等级"""
        if score >= 0.9:
            return 'A (Excellent)'
        elif score >= 0.75:
            return 'B (Good)'
        elif score >= 0.6:
            return 'C (Acceptable)'
        elif score >= 0.4:
            return 'D (Poor)'
        else:
            return 'F (Failed)'
    
    def _group_by_sample(self, trajectories: List[Dict]) -> Dict[int, Dict[str, str]]:
        """将轨迹按 sample_id 分组"""
        grouped = {}
        for traj in trajectories:
            sample_id = traj.get('meta', {}).get('sample_id', 0)
            agent_id = traj.get('agent_id', 'unknown')
            
            if sample_id not in grouped:
                grouped[sample_id] = {}
            
            # Extract response
            response = ''
            for msg in traj.get('messages', []):
                if msg.get('role') == 'assistant':
                    response = msg.get('content', '')
            
            grouped[sample_id][agent_id] = response
        
        return grouped
    
    # ============== Save Report ==============
    
    def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """保存评估报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"eval_report_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return filepath

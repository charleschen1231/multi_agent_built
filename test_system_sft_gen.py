"""Test System-Level SFT data generator"""
import json
from training.sft_trainer import SFTTrainer

t = SFTTrainer('./test_gen_output')

# Load config
with open('examples/system_sft_config.json', encoding='utf-8') as f:
    config = json.load(f)

# Generate data for all agents
result = t.prepare_all_agents_sft_data(
    config_json=config,
    dataset_file='data/system_sft_dataset.jsonl',
    log_callback=lambda msg: print(msg)
)

print("\n" + "=" * 50)
print("Results:")
for agent_id, data in result.items():
    print(f"  {agent_id}: {data.get('data_file', 'FAILED')}")
    if data.get('error'):
        print(f"    ERROR: {data['error']}")

# Verify first agent's output
print("\n" + "=" * 50)
print("Verifying planner output:")
planner_file = result.get('planner', {}).get('data_file')
if planner_file:
    with open(planner_file, encoding='utf-8') as f:
        first_line = json.loads(f.readline())
    msgs = first_line['messages']
    print(f"  Messages count: {len(msgs)}")
    for m in msgs:
        content = m['content'][:80] + "..." if len(m['content']) > 80 else m['content']
        print(f"  [{m['role']}] {content}")

print("\nVerifying infer output:")
infer_file = result.get('infer', {}).get('data_file')
if infer_file:
    with open(infer_file, encoding='utf-8') as f:
        first_line = json.loads(f.readline())
    msgs = first_line['messages']
    print(f"  Messages count: {len(msgs)}")
    for m in msgs:
        content = m['content'][:80] + "..." if len(m['content']) > 80 else m['content']
        print(f"  [{m['role']}] {content}")

print("\nVerifying checker output:")
checker_file = result.get('checker', {}).get('data_file')
if checker_file:
    with open(checker_file, encoding='utf-8') as f:
        first_line = json.loads(f.readline())
    msgs = first_line['messages']
    print(f"  Messages count: {len(msgs)}")
    for m in msgs:
        content = m['content'][:80] + "..." if len(m['content']) > 80 else m['content']
        print(f"  [{m['role']}] {content}")

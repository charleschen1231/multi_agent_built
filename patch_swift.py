#!/usr/bin/env python
"""修复 ms-swift 的 FSDPModule 导入问题"""

file_path = r'D:\work_apps\Anaconda\Anaconda3\Lib\site-packages\swift\callbacks\activation_cpu_offload.py'

# Read file
with open(file_path, 'r') as f:
    content = f.read()

# Replace
old_text = '''"""Functionality for CPU offloading of tensors saved for backward pass."""
import functools
import torch
from torch.distributed.fsdp import FSDPModule as FSDP2
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP'''

new_text = '''"""Functionality for CPU offloading of tensors saved for backward pass."""
import functools
import torch
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP

# Try to import FSDPModule (only available in newer PyTorch versions)
try:
    from torch.distributed.fsdp import FSDPModule as FSDP2
except ImportError:
    FSDP2 = None'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w') as f:
        f.write(content)
    print('File patched successfully')
else:
    print('Pattern not found, file may already be patched or changed')

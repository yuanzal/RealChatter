import torch

# 打印关键信息（复制到终端/脚本运行）
print("=== CUDA 检测详情 ===")
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 是否可用: {torch.cuda.is_available()}")
print(f"CUDA 版本: {torch.version.cuda if torch.cuda.is_available() else '无'}")
print(f"显卡数量: {torch.cuda.device_count() if torch.cuda.is_available() else '0'}")
print(f"显卡名称: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else '无'}")
print(f"PyTorch 编译时的 CUDA 版本: {torch._C._cuda_getCompiledVersion() if hasattr(torch._C, '_cuda_getCompiledVersion') else '无'}")
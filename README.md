# FFmpeg 视频加速处理工具

使用 FFmpeg 进行视频处理的 Python 工具，支持 Queue 和 SharedMemory 两种帧传输后端。

## 安装依赖

```bash
pip install opencv-python numpy tqdm
```

确保系统已安装 FFmpeg：
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`

## 使用方法

直接运行脚本（需要先准备 `test.mp4` 文件）：

```bash
python ffmpeg_speedup.py
```

或在代码中使用：

```python
from ffmpeg_speedup import process_video

# Queue 模式
process_video("input.mp4", "output_queue.mp4", backend_mode="queue")

# SharedMemory 模式（性能更好）
process_video("input.mp4", "output_shm.mp4", backend_mode="shm")
```

## 说明

- **Queue 模式**：使用进程队列传输帧，简单但需要复制数据
- **SharedMemory 模式**：使用共享内存传输帧，性能更优
- 输出视频：1280x720，30fps，H.264 编码

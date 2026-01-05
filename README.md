# FFmpeg 视频加速处理工具

使用 FFmpeg 进行视频处理的 Python 工具，支持 Queue 和 SharedMemory 两种帧传输后端，输入可为文件/RTSP/RTMP，输出可为文件或 RTMP 推流。

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

# 文件 -> 文件（Queue）
process_video("input.mp4", "output_queue.mp4", backend_mode="queue", is_stream_out=False)

# 文件 -> 文件（SharedMemory，性能更好）
process_video("input.mp4", "output_shm.mp4", backend_mode="shm", is_stream_out=False)

# RTSP -> RTMP 推流（SharedMemory）
process_video("rtsp://user:pass@ip:port/stream", "rtmp://localhost/live/stream", backend_mode="shm", is_stream_out=True)
```

## 说明

- **Queue 模式**：使用进程队列传输帧，简单但需要复制数据
- **SharedMemory 模式**：使用共享内存传输帧，性能更优
- 视频尺寸/帧率：默认 1280x720 @ 30fps，可在代码中修改
- 输出编码：H.264；当 `is_stream_out=True` 时以 FLV 封装推 RTMP


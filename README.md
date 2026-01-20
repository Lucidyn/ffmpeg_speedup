# FFmpeg 视频加速处理工具

使用 FFmpeg 进行视频处理的 Python 工具，支持 Queue 和 SharedMemory 两种帧传输后端，输入可为文件/RTSP/RTMP，输出可为文件或 RTMP 推流。

## 安装依赖

```bash
pip install opencv-python numpy tqdm
```

确保系统已安装 FFmpeg：
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
 - Windows: 可使用 `choco install ffmpeg` 或从 FFmpeg 官网下载解压并把 `ffmpeg.exe` 加入 PATH

## 使用方法（标准版）

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

## 使用方法（快速版）

快速版提供更低延迟与更高吞吐，采用线程化读写与低延迟参数，同时支持自动硬件解码。

```python
from ffmpeg_speedup_fast import process_video_fast

# 文件 -> 文件（默认使用 SharedMemory 后端）
process_video_fast("input.mp4", "out_fast.mp4", backend_mode="shm", is_stream_in=False, is_stream_out=False)

# RTSP -> RTMP 推流（低延迟、自动硬件加速）
process_video_fast(
    "rtsp://user:pass@ip:port/stream",
    "rtmp://localhost/live/stream",
    backend_mode="shm",
    is_stream_in=True,
    is_stream_out=True
)

# 可选参数：限制处理帧数、切换编码器/预设
process_video_fast(
    "input.mp4", "out_nvenc.flv",
    backend_mode="shm",
    is_stream_out=True,
    max_frames=300,
    encoder="libx264",     # 或者设置为 h264_nvenc（需 FFmpeg 支持 NVENC）
    preset="veryfast"      # 可选 ultrafast/veryfast/faster/...
)
```

## 快速版特性

- 线程化读写管线，减少同步等待与阻塞
- 低延迟参数：nobuffer、low_delay、zerolatency 等
- 自动硬件解码：`-hwaccel auto`（由 FFmpeg 根据环境选择）
- 默认使用 SharedMemory 后端，进一步降低拷贝开销
- 编码器可切换：`libx264` 或支持的硬件编码器（如 `h264_nvenc`）

- **Queue 模式**：使用进程队列传输帧，简单但需要复制数据
- **SharedMemory 模式**：使用共享内存传输帧，性能更优
- 视频尺寸/帧率：默认 1280x720 @ 30fps，可在代码中修改
- 输出编码：H.264；当 `is_stream_out=True` 时以 FLV 封装推 RTMP

## API

- 标准版：
  - `process_video(input_source, output_dest, backend_mode="queue", is_stream_out=False)`
    - `input_source`: 文件路径/RTSP/RTMP 地址
    - `output_dest`: 输出文件路径或 RTMP 推流地址
    - `backend_mode`: `"queue"` 或 `"shm"`
    - `is_stream_out`: `True` 时输出封装为 FLV 用于 RTMP
- 快速版：
  - `process_video_fast(input_source, output_dest, backend_mode="shm", is_stream_in=False, is_stream_out=False, max_frames=None, encoder="libx264", preset="veryfast")`
    - `is_stream_in`: 流输入（如 RTSP）建议设为 `True`，启用低延迟参数
    - `max_frames`: 限制处理的帧数，用于测试或压测
    - `encoder`: 编码器，默认 `libx264`；若 FFmpeg 支持可用 `h264_nvenc`
    - `preset`: 编码预设，`ultrafast/veryfast/faster/...`

## 性能与调优建议

- 后端选择：优先使用 `SharedMemory (shm)`，减少数据拷贝
- 低延迟输入：RTSP 建议 `is_stream_in=True`，并使用 TCP 传输
- 编码器选择：
  - CPU：`libx264 + preset=veryfast/ultrafast`
  - GPU（NVIDIA）：`h264_nvenc`（需 FFmpeg 编译支持 NVENC）
- GOP 设置：快速版默认 `-g = fps*2`，平衡延迟与压缩效率
- 线程化管线：快速版采用读写线程并行，提高吞吐

## 注意事项

- 需要系统可执行的 `ffmpeg`，且 PATH 配置正确
- 推流目标（如 `rtmp://localhost/live/stream`）需事先启动接收端
- 不同平台的硬件加速可用性由 FFmpeg 环境决定（`-hwaccel auto` 会自动选择）

- 输出编码：H.264；当 `is_stream_out=True` 时以 FLV 封装推 RTMP


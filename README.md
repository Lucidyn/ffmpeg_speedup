# FFmpeg 视频加速处理工具

使用 FFmpeg 进行视频处理的 Python 工具，支持 Queue 和 SharedMemory 两种帧传输后端，输入可为文件/RTSP/RTMP，输出可为文件或 RTMP 推流。

## 项目特性

- **双模式后端**：支持 Queue（简单但需复制数据）和 SharedMemory（性能更优）两种帧传输方式
- **灵活的输入源**：支持本地文件、RTSP 流、RTMP 流
- **多样化输出**：支持保存为文件或推流至 RTMP 服务器
- **FPS 实时监控**：集成进度条，实时显示处理帧率
- **统计信息**：处理完成后输出总帧数、处理时间、平均 FPS

## 安装依赖

```bash
pip install opencv-python numpy tqdm
```

确保系统已安装 FFmpeg：
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- Windows: 可使用 `choco install ffmpeg` 或从 FFmpeg 官网下载解压并把 `ffmpeg.exe` 加入 PATH

## 使用示例

### 示例 1：使用标准 process_video() 进行文件处理

```python
from ffmpeg_speedup import process_video

# 使用 Queue 后端处理文件
process_video("input.mp4", "output_queue.mp4", backend_mode="queue", is_stream_out=False)

# 使用 SharedMemory 后端处理文件（更快）
process_video("input.mp4", "output_shm.mp4", backend_mode="shm", is_stream_out=False)

# RTSP 流直接推送至 RTMP
process_video(
    "rtsp://user:pass@ip:port/stream",
    "rtmp://localhost/live/stream",
    backend_mode="shm",
    is_stream_out=True
)
```

### 示例 2：使用 FastVideoReader 进行高性能读取

```python
from ffmpeg_decode import FastVideoReader
import time
import numpy as np

# 初始化读取器（5 帧循环缓冲）
reader = FastVideoReader("input.mp4", width=1280, height=720, buffer_size=5)
reader.start()

frame_count = 0
start_time = time.time()

try:
    while True:
        frame = reader.get_latest_frame()
        
        if frame is not None:
            # 对帧进行处理（例如：推理、统计等）
            # mean_color = np.mean(frame, axis=(0, 1))
            
            frame_count += 1
            
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"Processed: {frame_count} frames, FPS: {fps:.2f}")
        
        time.sleep(0.001)  # 防止 CPU 100% 占用

except KeyboardInterrupt:
    print("Stopping...")
finally:
    reader.stop()
    elapsed = time.time() - start_time
    print(f"Total frames: {frame_count}, Duration: {elapsed:.2f}s")
```

### 示例 3：RTSP 流实时处理

```python
from ffmpeg_decode import FastVideoReader
import cv2
import time

# RTSP 流读取
reader = FastVideoReader("rtsp://user:pass@ip:port/stream", width=1280, height=720)
reader.start()

try:
    while True:
        frame = reader.get_latest_frame()
        if frame is not None:
            # 例如：推理或实时处理
            # 若需要修改，请调用 .copy() 复制一份
            frame_copy = frame.copy()
            
            # 你的处理代码...
            
        time.sleep(0.001)
except KeyboardInterrupt:
    pass
finally:
    reader.stop()
```

## 核心模块

### ffmpeg_speedup.py - 标准处理模式

#### FrameBackend 类
处理帧的存取，支持两种模式：
- **queue 模式**：使用多进程队列（maxsize=10），简单直观，但需要复制帧数据
- **shm 模式**：使用共享内存，性能更优，适合高帧率处理

#### FFmpegPipe 类
负责 FFmpeg 的编码/解码过程：
- **decode()** 方法：启动 FFmpeg 解码进程，支持各种输入源
- **encode()** 方法：启动 FFmpeg 编码进程，支持文件和流输出
  - 输出格式：H.264 视频编码 + yuv420p 像素格式
  - 推流模式（is_stream=True）：使用 FLV 容器格式用于 RTMP

### ffmpeg_decode.py - 高性能视频读取后端

#### FastVideoReader 类
完全脱离 GUI 依赖的高性能视频/流读取后端，采用循环缓冲区和零拷贝设计：

**主要特性：**
- **后台解码进程**：独立进程进行 FFmpeg 解码，不阻塞主线程
- **共享内存缓冲区**：使用循环缓冲区存储视频帧，支持 N 帧 buffer（默认 5 帧）
- **零拷贝视图**：使用 NumPy 视图映射共享内存，只在需要时复制数据
- **自动硬件加速**：启用 `-hwaccel auto` 自动选择硬件解码器
- **流式读取**：支持文件、RTSP、RTMP 等各种输入源
- **元数据同步**：通过共享内存传递最新帧索引和总帧数

**关键方法：**
- `__init(source, width, height, buffer_size=5)`：初始化读取器
- `start()`：启动后台读取进程
- `get_latest_frame()`：获取最新一帧（零拷贝）
- `stop()`：优雅释放所有资源

## API 文档

### ffmpeg_speedup.py API

#### process_video()

```python
process_video(input_source, output_dest, backend_mode="queue", is_stream_out=False)
```

**参数说明：**
- `input_source` (str)：输入源，可为文件路径、RTSP URL 或 RTMP URL
- `output_dest` (str)：输出目标，可为文件路径或 RTMP 推流地址
- `backend_mode` (str)：帧传输后端，可选值为 `"queue"` 或 `"shm"`，默认为 `"queue"`
- `is_stream_out` (bool)：输出是否为流推送，`True` 时使用 FLV 格式推 RTMP，默认为 `False`

**处理流程：**
1. 初始化视频分辨率为 1280x720，帧率为 30fps
2. 启动 FFmpeg 解码进程读取输入
3. 解码的帧写入后端存储
4. 从后端读取帧进行编码
5. 编码的帧写入 FFmpeg 编码进程
6. 实时显示处理进度和 FPS
7. 完成后输出统计信息

### ffmpeg_decode.py API

#### FastVideoReader 类

```python
from ffmpeg_decode import FastVideoReader

# 初始化读取器
reader = FastVideoReader(
    source="input.mp4",      # 文件路径或 RTSP/RTMP URL
    width=1280,              # 输出宽度
    height=720,              # 输出高度
    buffer_size=5            # 循环缓冲区大小（帧数）
)

# 启动后台读取进程
reader.start()

# 在主线程中获取最新帧
while True:
    frame = reader.get_latest_frame()  # 获取最新一帧（零拷贝）
    if frame is not None:
        # 处理帧数据
        pass
    time.sleep(0.001)  # 防止 CPU 空转

# 清理资源
reader.stop()
```

**FastVideoReader 方法：**
- `start()`：启动后台读取进程
- `get_latest_frame()`：获取最新一帧（NumPy 视图，非拷贝）
- `stop()`：释放共享内存和进程资源

**工作流程：**
1. 后台进程持续读取 FFmpeg 解码的帧
2. 帧数据存储在循环缓冲区（共享内存）
3. 主进程通过 `get_latest_frame()` 获取最新帧的视图
4. 调用 `.copy()` 时才执行真正的数据复制

## 性能对比与选择指南

### 三种使用方式的对比

| 特性 | process_video (Queue) | process_video (SharedMemory) | FastVideoReader |
|------|-----|------|------|
| **数据拷贝次数** | 多次 | 1 次 | 0 次（视图） |
| **吞吐性能** | 中等 | 高 | 最高 |
| **延迟** | 中等 | 低 | 最低 |
| **易用性** | 最简单 | 简单 | 需自己处理循环 |
| **适用场景** | 低帧率批处理 | 文件转换 | 实时流处理、AI 推理 |
| **编码输出** | ✓（自带） | ✓（自带） | ✗（需自己实现） |
| **支持的源** | 文件/RTSP/RTMP | 文件/RTSP/RTMP | 文件/RTSP/RTMP |

### 选择建议

- **批量转码文件**：使用 `process_video()` + `backend_mode="shm"`
- **RTSP → RTMP 推流**：使用 `process_video()` + `backend_mode="shm"`，`is_stream_out=True`
- **实时流处理 + AI 推理**：使用 `FastVideoReader`（最小延迟和 CPU 占用）
- **简单脚本**：使用 `process_video()` + `backend_mode="queue"`

## 调优建议

### 硬件加速
FastVideoReader 默认启用 `-hwaccel auto`，自动选择系统支持的硬件解码器。对于特定场景，可修改：
```python
# 若有 NVIDIA GPU，可改为：
# cmd 中改为: "-hwaccel", "cuda"

# 若有 Intel 快速同步，可改为：
# cmd 中改为: "-hwaccel", "qsv"
```

### 缓冲区大小
- `buffer_size=5`：默认值，适合大多数场景
- 若处理延迟较高，可增大 buffer_size（如 10-20）
- 若需要最小延迟，可减小 buffer_size（如 1-2）

### 分辨率与帧率
- `process_video()`：默认 1280x720 @ 30fps，可在代码中调整
- `FastVideoReader`：初始化时指定 width 和 height

### 输入源优化
- **本地文件**：直接使用文件路径
- **RTSP/RTMP 流**：
  - 使用 FastVideoReader 获得最小延迟
  - SharedMemory 后端相比 Queue 后端更稳定
  - TCP 传输比 UDP 更可靠

### CPU 优化
- FastVideoReader 采用后台进程解码，主线程可进行 AI 推理等计算密集操作
- 避免在获取帧后立即调用 `.copy()`，除非必要
- 使用 `time.sleep(0.001)` 防止 CPU 100% 占用

## 注意事项

- 确保系统已正确安装 FFmpeg，且 `ffmpeg` 命令在 PATH 中可访问
- 推流到 RTMP 服务器时，需提前启动接收端（如 Nginx RTMP 服务器）
- Queue 后端的 maxsize 为 10，高帧率下可能会出现丢帧，此时建议使用 SharedMemory 后端
- 处理大型视频文件时，SharedMemory 后端需要足够的内存空间
- FastVideoReader 的共享内存需要足够的系统内存（每帧约 2.7 MB @ 1280x720 BGR24）

## 项目文件说明

- `ffmpeg_speedup.py`：标准处理模式，包含 FrameBackend、FFmpegPipe 类和 process_video() 函数
- `ffmpeg_decode.py`：高性能视频读取后端，包含 FastVideoReader 类，专为实时流处理和 AI 推理优化
- `README.md`：项目文档


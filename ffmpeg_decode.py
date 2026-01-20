import numpy as np
import subprocess
import time
import os
from multiprocessing import Process, Event, shared_memory

class FastVideoReader:
    """高性能视频/流读取后端：完全脱离 GUI 依赖"""
    def __init__(self, source, width, height, buffer_size=5):
        self.source = source
        self.width = width
        self.height = height
        self.frame_size = width * height * 3 # BGR24 格式
        self.buffer_size = buffer_size
        
        # 1. 初始化共享内存
        # 用于存储图像数据
        self.shm = shared_memory.SharedMemory(create=True, size=self.frame_size * buffer_size)
        # 用于存储元数据（如最新帧的索引和总帧数）
        self.meta_shm = shared_memory.SharedMemory(create=True, size=16) 
        
        self.stop_event = Event()
        self.process = None

    def _reader_loop(self):
        """独立解码进程"""
        # 优化建议：如果是 NVIDIA GPU，可将 -hwaccel auto 改为 -hwaccel cuda
        cmd = [
            "ffmpeg", 
            "-hwaccel", "auto", 
            "-i", self.source,
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-vf", f"scale={self.width}:{self.height}",
            "-vsync", "0", 
            "pipe:1"
        ]
        
        # 开启 FFmpeg 子进程
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        idx = 0
        meta_arr = np.frombuffer(self.meta_shm.buf, dtype=np.int64)
        
        try:
            while not self.stop_event.is_set():
                raw_frame = proc.stdout.read(self.frame_size)
                if not raw_frame or len(raw_frame) < self.frame_size:
                    break
                
                # 计算循环缓冲区位置
                write_idx = idx % self.buffer_size
                offset = write_idx * self.frame_size
                
                # 直接操作共享内存缓冲区
                self.shm.buf[offset:offset + self.frame_size] = raw_frame
                
                # 更新最新的帧索引，供主进程读取
                meta_arr[0] = write_idx # 最新帧索引
                meta_arr[1] = idx       # 总计读取帧数
                idx += 1
        finally:
            proc.terminate()
            proc.wait()

    def start(self):
        """启动后台读取进程"""
        self.process = Process(target=self._reader_loop, daemon=True)
        self.process.start()

    def get_latest_frame(self):
        """主进程获取最新的一帧（零拷贝视图）"""
        meta_arr = np.frombuffer(self.meta_shm.buf, dtype=np.int64)
        latest_idx = meta_arr[0]
        
        if latest_idx < 0:
            return None
        
        offset = int(latest_idx) * self.frame_size
        # 使用 ndarray 视图映射共享内存，只在需要时通过 .copy() 复制
        frame_data = np.frombuffer(self.shm.buf[offset:offset + self.frame_size], dtype=np.uint8)
        return frame_data.reshape((self.height, self.width, 3))

    def stop(self):
        """释放资源"""
        self.stop_event.set()
        if self.process:
            self.process.join(timeout=1)
        self.shm.close()
        self.shm.unlink()
        self.meta_shm.close()
        self.meta_shm.unlink()

# --- 纯数据处理示例 ---
if __name__ == "__main__":
    # 配置参数
    INPUT_SOURCE = "test.mp4" # 也可以是 "rtsp://..."
    WIDTH, HEIGHT = 1280, 720
    
    reader = FastVideoReader(INPUT_SOURCE, WIDTH, HEIGHT)
    reader.start()
    
    print(f"Starting stream processing: {WIDTH}x{HEIGHT}...")
    
    # 初始化元数据
    np.frombuffer(reader.meta_shm.buf, dtype=np.int64)[:] = -1
    
    start_time = time.time()
    processed_count = 0
    
    try:
        while True:
            frame = reader.get_latest_frame()
            
            if frame is not None:
                # --- 在这里进行你的后续处理 ---
                # 示例：简单的像素统计或传递给 AI 模型
                # mean_color = np.mean(frame, axis=(0, 1)) 
                
                processed_count += 1
                
                # 每 100 帧打印一次进度
                if processed_count % 100 == 0:
                    elapsed = time.time() - start_time
                    fps = processed_count / elapsed
                    print(f"Processed frames: {processed_count}, Current FPS: {fps:.2f}")
            
            # 模拟处理延迟或防止 CPU 空转
            time.sleep(0.001) 
            
            # 如果是处理文件，可以根据需要设置退出逻辑
            # if reader.stop_event.is_set(): break

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.stop()
        print(f"Total processed: {processed_count} frames.")
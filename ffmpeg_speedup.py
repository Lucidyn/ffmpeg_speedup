import os
import time
import numpy as np
from multiprocessing import Process, Queue, Lock
from multiprocessing import shared_memory

import cv2
import subprocess
import logging
from tqdm import tqdm

class FrameBackend:
    """双模式帧存取后端"""
    def __init__(self, width, height, mode="queue"):
        self.width = width
        self.height = height
        self.frame_size = width * height * 3
        self.mode = mode
        self.lock = Lock()
        if mode == "queue":
            self.queue = Queue(maxsize=10)
        elif mode == "shm":
            self.shm = shared_memory.SharedMemory(create=True, size=self.frame_size)
        else:
            raise ValueError("mode must be 'queue' or 'shm'")

    def write(self, frame: np.ndarray):
        if self.mode == "queue":
            try:
                self.queue.put_nowait(frame.copy())
            except:
                pass  # 队列满丢帧
        else:
            with self.lock:
                np.copyto(np.ndarray((self.height, self.width, 3), dtype=np.uint8, buffer=self.shm.buf), frame)

    def read(self):
        if self.mode == "queue":
            try:
                return self.queue.get_nowait()
            except:
                return None
        else:
            with self.lock:
                return np.ndarray((self.height, self.width, 3), dtype=np.uint8, buffer=self.shm.buf).copy()

    def stop(self):
        if self.mode == "queue":
            while not self.queue.empty():
                self.queue.get()
        else:
            self.shm.close()
            self.shm.unlink()

class FFmpegPipe:
    def __init__(self, width, height, fps=30):
        self.width = width
        self.height = height
        self.fps = fps

    def decode(self, input_source):
        """支持文件/RTSP/RTMP输入"""
        cmd = [
            "ffmpeg", "-i", input_source,
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-vf", f"scale={self.width}:{self.height}",
            "pipe:1"
        ]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def encode(self, output_dest, is_stream=False):
        """支持文件/RTMP输出"""
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", f"{self.width}x{self.height}",
            "-r", str(self.fps),
            "-i", "pipe:0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p"
        ]
        if is_stream:
            cmd += ["-f", "flv"]
        cmd.append(output_dest)
        return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

def process_video(input_source, output_dest, backend_mode="queue", is_stream_out=False):
    width, height = 1280, 720
    backend = FrameBackend(width, height, mode=backend_mode)
    ff = FFmpegPipe(width, height, fps=30)
    dec_proc = ff.decode(input_source)
    enc_proc = ff.encode(output_dest, is_stream=is_stream_out)

    frame_count = 0
    start_time = time.time()
    pbar = tqdm(desc=f"{backend_mode} processing", ncols=100, unit="frame")

    while True:
        raw_frame = dec_proc.stdout.read(width * height * 3)
        if not raw_frame or len(raw_frame) < width * height * 3:
            break
        frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))

        # 写入 backend
        backend.write(frame)

        # 读取后编码
        enc_frame = backend.read()
        if enc_frame is not None:
            enc_proc.stdin.write(enc_frame.tobytes())

        frame_count += 1
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            pbar.set_postfix_str(f"FPS: {fps:.2f}")
        pbar.update(1)

    dec_proc.stdout.close()
    enc_proc.stdin.close()
    dec_proc.wait()
    enc_proc.wait()
    backend.stop()
    pbar.close()

    total_time = time.time() - start_time
    print(f"[{backend_mode}] Total frames: {frame_count}, Total time: {total_time:.2f}s, Avg FPS: {frame_count/total_time:.2f}")

if __name__ == "__main__":
    # 文件输入输出示例
    input_file = "test.mp4"
    output_file = "out_queue.mp4"
    print("Processing file with Queue backend...")
    process_video(input_file, output_file, backend_mode="queue", is_stream_out=False)

    shm_output_file = "out_queue_shm.mp4"
    print("Processing file with Shm backend...")
    process_video(input_file, shm_output_file, backend_mode="shm", is_stream_out=False)

    # RTSP/RTMP示例
    # rtsp_input = "rtsp://username:password@ip:port/stream"
    # rtmp_output = "rtmp://localhost/live/stream"
    # print("\nProcessing RTSP->RTMP with SharedMemory backend...")
    # process_video(rtsp_input, rtmp_output, backend_mode="shm", is_stream_out=True)

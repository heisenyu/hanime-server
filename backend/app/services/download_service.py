import asyncio
import os
import time
import math
import json
from typing import Dict, Optional, List, Set, Any
from fastapi import WebSocket
from datetime import datetime
import httpx
import aiosqlite
from app.models.download import DownloadStatus, DownloadSegment, DownloadProgress
from app.services.video_service import VideoService
from app.config import settings, logger
import aiofiles.os
from urllib.parse import urlparse


class DownloadManager:
    """下载管理器"""
    
    def __init__(self):
        self.active_downloads: Dict[str, DownloadProgress] = {}
        self.websocket_connections: Set[WebSocket] = set()
        self.pause_events: Dict[str, asyncio.Event] = {}
        self.cancel_events: Dict[str, bool] = {}
        self.video_service = VideoService()
        
        # 配置参数
        # chunk_size: 每次从HTTP连接读取的数据块大小，影响内存使用和请求频率
        # 值越大，单次请求获取的数据越多，但占用内存也越多
        self.chunk_size = 1024 * 1024 * 4  # 4MB，调小以提高响应速度
        
        # buffer_size: 写入文件前在内存中累积的数据量
        # 较大的缓冲区可以减少磁盘I/O操作次数，提高性能
        self.buffer_size = 1024 * 1024 * 8   # 8MB
        
        # max_segments: 最大并发下载段数，影响并行度
        # 值越大并行度越高，但会增加系统和网络负载
        self.max_segments = 8  # 提高并发度
        
        # min_segment_size: 单个下载段的最小大小
        # 用于计算文件应该分成多少段，防止段过小导致性能下降
        # 文件总大小必须大于min_segment_size*2才会使用分段下载
        self.min_segment_size = 1024 * 1024 * 64  # 20MB，调小以适应更多文件使用分段下载
        
        # max_retries: 下载失败时的最大重试次数
        # 增加此值可以提高下载成功率，但可能导致长时间卡在失败的下载上
        self.max_retries = 5  # 增加重试次数提高可靠性
        
        # timeout: HTTP请求的超时时间(秒)
        # 较大的值适合网络不稳定的情况，较小的值可以更快检测到连接问题
        self.timeout = 10.0  # 适当减少超时时间
        
        # progress_update_interval: 更新下载进度的时间间隔(秒)
        # 值越小实时性越高，但会增加数据库操作和WebSocket通信频率
        self.progress_update_interval = 0.2  # 减少间隔提高实时性
        
        # 自适应参数
        self.bandwidth_samples = []  # 存储带宽样本用于自适应调整
        self.segment_adjust_threshold = 5  # 需要多少个样本才考虑调整段数
        self.connection_pool_size = 20  # HTTP连接池大小
        self.ws_batch_updates = True  # 启用WebSocket批量更新
        self.ws_throttle_interval = 0.1  # WebSocket节流间隔(秒)
        self.last_ws_update_time = {}  # 记录每个下载最后一次WS更新时间
        
        # 连接池
        self.http_clients = {}  # 存储基于域名的HTTP客户端连接池
        
        # 数据库路径
        self.db_path = settings.DB_PATH / "downloads.db"

    
    async def init_db(self):
        """初始化数据库"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                video_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT,
                cover_url TEXT,
                url TEXT NOT NULL,
                total_size INTEGER,
                downloaded INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3
            )
            """)
            await conn.commit()
    
    async def get_download_history(self) -> List[Dict[str, Any]]:
        """获取下载历史"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM downloads ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def load_downloads(self):
        """从数据库加载下载历史"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM downloads WHERE status IN ('downloading', 'paused') ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    video_id = row['video_id']
                    # 安全地获取列值，处理可能不存在的列
                    retry_count = 0
                    if 'retry_count' in row.keys():
                        retry_count = row['retry_count']
                    
                    max_retries = 3
                    if 'max_retries' in row.keys():
                        max_retries = row['max_retries']
                    
                    self.active_downloads[video_id] = DownloadProgress(
                        video_id=video_id,
                        filename=row['filename'],
                        title=row['title'],
                        cover_url=row['cover_url'],
                        total_size=row['total_size'] or 0,
                        downloaded=row['downloaded'] or 0,
                        status=row['status'],
                        speed=0.0,
                        error_message=row['error_message'],
                        url=row['url'],
                        created_at=row['created_at'],
                        completed_at=row['completed_at'],
                        retry_count=retry_count,
                        max_retries=max_retries
                    )
                    # 恢复暂停状态
                    if row['status'] == DownloadStatus.PAUSED:
                        self.pause_events[video_id] = asyncio.Event()
                        self.pause_events[video_id].clear()
                    elif row['status'] == DownloadStatus.DOWNLOADING:
                        self.pause_events[video_id] = asyncio.Event()
                        self.pause_events[video_id].set()
                        # 重新启动下载
                        output_path = settings.DOWNLOAD_PATH / row['filename']
                        asyncio.create_task(
                            self.download_file(
                                video_id,
                                row['url'],
                                output_path,
                                resume=True
                            )
                        )

    async def broadcast_progress(self, video_id: str):
        """向所有连接的客户端广播下载进度，使用节流控制更新频率"""
        if video_id not in self.active_downloads:
            return
            
        # 检查是否需要更新（节流控制）
        current_time = asyncio.get_event_loop().time()
        last_update = self.last_ws_update_time.get(video_id, 0)
        if current_time - last_update < self.ws_throttle_interval and self.active_downloads[video_id].status == DownloadStatus.DOWNLOADING:
            # 如果间隔太小且不是关键状态变更，则跳过此次更新
            return
            
        # 更新最后更新时间
        self.last_ws_update_time[video_id] = current_time
            
        progress_data = self.active_downloads[video_id].dict()
        progress_data['speed'] = round(progress_data['speed'], 2)
        
        # 确保datetime对象被转换为ISO格式字符串
        if isinstance(progress_data['created_at'], datetime):
            progress_data['created_at'] = progress_data['created_at'].isoformat()
        if 'completed_at' in progress_data and isinstance(progress_data['completed_at'], datetime):
            progress_data['completed_at'] = progress_data['completed_at'].isoformat()
            
        message = json.dumps(progress_data)
        
        # 使用批处理发送以减少WebSocket压力
        failed_connections = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                failed_connections.append(websocket)
                logger.error(f"WebSocket发送失败: {str(e)}")
                
        # 移除失败的连接
        for ws in failed_connections:
            try:
                self.websocket_connections.remove(ws)
            except:
                pass

    async def update_db(self, video_id: str, **kwargs):
        """更新数据库中的下载记录"""
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE downloads SET {set_clause} WHERE video_id = ?",
                [*values, video_id]
            )
            await db.commit()
    
    async def download_file(self, video_id: str, url: str, output_path, resume: bool = False):
        """下载文件并更新进度"""
        if video_id not in self.active_downloads:
            raise Exception("无效的下载ID")

        # 创建暂停事件（如果不存在）
        if video_id not in self.pause_events:
            self.pause_events[video_id] = asyncio.Event()
            self.pause_events[video_id].set()
            
        # 初始化取消标志
        self.cancel_events[video_id] = False

        try:
            # 创建下载目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 获取复用的HTTP客户端
            client = await self.get_http_client(url)
            
            # 检查服务器是否支持范围请求
            try:
                # 使用较短的超时进行HEAD请求
                head_timeout = min(5.0, self.timeout)
                response = await client.head(url, timeout=head_timeout)
                accept_ranges = response.headers.get("accept-ranges", "").lower() == "bytes"
                total_size = int(response.headers.get("content-length", 0))
                    
                if total_size == 0:
                    # 如果HEAD请求没有返回文件大小，尝试GET请求
                    # 仅请求文件头部以获取大小信息
                    headers = {"Range": "bytes=0-8191"}  # 只请求前8KB
                    async with client.stream('GET', url, headers=headers) as response:
                        # 检查是否支持范围请求
                        if response.status_code == 206:
                            accept_ranges = True
                            content_range = response.headers.get("content-range", "")
                            if content_range and "/*" in content_range:
                                # 解析总大小
                                try:
                                    total_size = int(content_range.split("/")[1])
                                except ValueError:
                                    pass
                            
                        if total_size == 0:
                            # 如果仍然无法获取大小，则完整请求一次（但不下载）
                            async with client.stream('GET', url) as full_response:
                                total_size = int(full_response.headers.get("content-length", 0))
                                if total_size == 0:
                                    raise Exception("无法获取文件大小")
            except Exception as e:
                raise Exception(f"获取文件信息失败: {str(e)}")

            # 检查文件是否已存在且完整
            if os.path.exists(output_path) and not resume:
                file_size = os.path.getsize(output_path)
                if file_size == total_size:
                    self.active_downloads[video_id].status = DownloadStatus.COMPLETED
                    self.active_downloads[video_id].downloaded = file_size
                    self.active_downloads[video_id].total_size = file_size
                    await self.update_db(
                        video_id,
                        status=DownloadStatus.COMPLETED,
                        downloaded=file_size,
                        total_size=file_size,
                        completed_at=datetime.now()
                    )
                    await self.broadcast_progress(video_id)
                    return

            # 更新数据库中的总大小
            if not resume:
                await self.update_db(video_id, total_size=total_size)
            
            # 初始化或更新进度
            self.active_downloads[video_id].total_size = total_size
            self.active_downloads[video_id].status = DownloadStatus.DOWNLOADING
            
            # 动态确定是否使用分段下载及分段数量
            use_segmented_download = accept_ranges and total_size > self.min_segment_size * 2
            
            # 使用自适应分段算法
            optimal_segments = self.calculate_optimal_segments(total_size)
            logger.info(f"文件大小: {total_size} 字节, 自适应计算最佳段数: {optimal_segments}")
            
            if use_segmented_download:
                # 分段下载
                await self.segmented_download(video_id, url, output_path, total_size, resume, optimal_segments)
            else:
                # 单线程下载
                await self.simple_download(video_id, url, output_path, total_size, resume)
                
        except Exception as e:
            error_message = f"下载失败: {str(e)}"
            if video_id in self.active_downloads:
                self.active_downloads[video_id].status = DownloadStatus.ERROR
                self.active_downloads[video_id].error_message = error_message
                await self.update_db(
                    video_id,
                    status=DownloadStatus.ERROR,
                    error_message=error_message
                )
                await self.broadcast_progress(video_id)
            if os.path.exists(output_path) and not resume:
                try:
                    os.remove(output_path)
                except Exception as e:
                    logger.error(f"删除文件失败: {str(e)}")
        finally:
            # 清理暂停和取消事件
            if video_id in self.active_downloads and not (self.active_downloads[video_id].status == DownloadStatus.PAUSED):
                self.pause_events.pop(video_id, None)
                self.cancel_events.pop(video_id, None)
                
    def calculate_optimal_segments(self, file_size: int) -> int:
        """
        根据文件大小和历史带宽动态计算最佳分段数
        
        自适应算法策略:
        1. 文件越大，段数越多
        2. 根据以往下载速度动态调整
        3. 控制每个段的大小在合理范围内
        4. 考虑系统资源限制
        """
        # 默认基于文件大小的初始值
        base_segments = min(
            self.max_segments,  # 不超过最大限制
            max(1, file_size // (self.min_segment_size))  # 至少保证每段大小合理
        )
        
        # 如果有足够的带宽样本，考虑调整
        if len(self.bandwidth_samples) >= self.segment_adjust_threshold:
            avg_bandwidth = sum(self.bandwidth_samples) / len(self.bandwidth_samples)
            
            # 带宽较高时增加并发度，带宽较低时减少并发度
            # 以5MB/s为基准带宽
            base_bandwidth = 5 * 1024 * 1024  # 5MB/s
            bandwidth_factor = min(2.0, max(0.5, avg_bandwidth / base_bandwidth))
            
            adjusted_segments = round(base_segments * bandwidth_factor)
            return min(self.max_segments, max(1, adjusted_segments))
            
        return base_segments

    async def segmented_download(self, video_id: str, url: str, output_path, total_size: int, resume: bool = False, num_segments: int = None):
        """使用分段并发下载，支持自适应分段"""
        try:
            # 初始化时间和计数器
            last_update_time = asyncio.get_event_loop().time()
            last_downloaded = 0
            start_time = asyncio.get_event_loop().time()
            
            # 使用传入的段数或计算最佳段数
            if num_segments is None:
                num_segments = min(self.max_segments, max(1, total_size // self.min_segment_size))
                
            # 计算每个段的大小，使用自适应大小
            segment_size = math.ceil(total_size / num_segments)
            logger.info(f"文件大小: {total_size} 字节, 使用 {num_segments} 个下载段, 每段大小约 {segment_size} 字节")
            
            # 如果是恢复下载，检查哪些段已经完成
            if resume and hasattr(self.active_downloads[video_id], 'segments') and self.active_downloads[video_id].segments:
                segments = self.active_downloads[video_id].segments
                # 计算已下载量
                total_downloaded = sum(seg.downloaded for seg in segments)
                self.active_downloads[video_id].downloaded = total_downloaded
            else:
                # 创建新段，使用优化的段大小分配
                segments = []
                
                # 优化分段：前半部分段稍小，后半部分段略大，提高启动速度
                front_segments = max(1, num_segments // 3)  # 前1/3的段
                front_segment_size = segment_size * 0.8     # 前段略小
                back_segment_size = segment_size * 1.1      # 后段略大
                
                # 确保总大小保持不变
                total_front_size = front_segment_size * front_segments
                remaining_size = total_size - total_front_size
                back_segments = num_segments - front_segments
                
                if back_segments > 0:
                    back_segment_size = remaining_size / back_segments
                
                # 创建前部分段
                total_allocated = 0
                for i in range(front_segments):
                    start = total_allocated
                    allocated_size = int(front_segment_size)
                    if i == front_segments - 1:
                        # 最后一个前段可能需要调整大小
                        allocated_size = int(total_front_size - total_allocated)
                    end = min(start + allocated_size - 1, total_size - 1)
                    segments.append(DownloadSegment(start=start, end=end))
                    total_allocated += allocated_size
                
                # 创建后部分段
                for i in range(back_segments):
                    start = total_allocated
                    allocated_size = int(back_segment_size)
                    if i == back_segments - 1:
                        # 最后一段确保覆盖剩余所有字节
                        end = total_size - 1
                    else:
                        end = min(start + allocated_size - 1, total_size - 1)
                    segments.append(DownloadSegment(start=start, end=end))
                    total_allocated += allocated_size
                
                # 更新下载对象
                self.active_downloads[video_id].segments = segments
                
                # 创建空文件
                with open(output_path, "wb") as f:
                    f.seek(total_size - 1)
                    f.write(b'\0')
            
            # 创建下载任务，使用信号量控制并发
            semaphore = asyncio.Semaphore(num_segments)
            tasks = []
            for i, segment in enumerate(segments):
                if segment.status != "completed":
                    task = asyncio.create_task(
                        self.download_segment(
                            video_id, url, output_path, segment, i, semaphore
                        )
                    )
                    tasks.append(task)
            
            # 定时更新进度
            update_progress_task = asyncio.create_task(
                self.update_segmented_progress(
                    video_id, segments, last_update_time, last_downloaded
                )
            )
            
            # 等待所有下载任务完成
            await asyncio.gather(*tasks)
            
            # 取消更新进度任务
            update_progress_task.cancel()
            
            # 检查是否所有段都已完成
            all_completed = all(segment.status == "completed" for segment in segments)
            if all_completed:
                total_downloaded = total_size
                self.active_downloads[video_id].status = DownloadStatus.COMPLETED
                self.active_downloads[video_id].downloaded = total_downloaded
                completed_at = datetime.now()
                await self.update_db(
                    video_id,
                    status=DownloadStatus.COMPLETED,
                    downloaded=total_downloaded,
                    completed_at=completed_at
                )
                self.active_downloads[video_id].completed_at = completed_at
                
                # 计算带宽样本并存储
                elapsed_time = asyncio.get_event_loop().time() - start_time
                if elapsed_time > 0:
                    bandwidth = total_size / elapsed_time  # bytes/second
                    # 保留最新的10个样本
                    self.bandwidth_samples.append(bandwidth)
                    if len(self.bandwidth_samples) > 10:
                        self.bandwidth_samples.pop(0)
                
            else:
                # 如果有段下载失败，整体下载失败
                self.active_downloads[video_id].status = DownloadStatus.ERROR
                self.active_downloads[video_id].error_message = "部分段下载失败"
                await self.update_db(
                    video_id,
                    status=DownloadStatus.ERROR,
                    error_message="部分段下载失败"
                )
            
            await self.broadcast_progress(video_id)
                
        except Exception as e:
            raise Exception(f"分段下载失败: {str(e)}")
    
    async def update_segmented_progress(self, video_id: str, segments: List[DownloadSegment], last_update_time, last_downloaded):
        """定期更新分段下载的进度"""
        try:
            while True:
                # 检查是否被取消
                if self.cancel_events.get(video_id):
                    return
                
                # 等待暂停事件
                await self.pause_events[video_id].wait()
                
                # 计算总下载量
                downloaded = sum(segment.downloaded for segment in segments)
                
                # 计算下载速度
                current_time = asyncio.get_event_loop().time()
                time_diff = current_time - last_update_time
                if time_diff >= self.progress_update_interval:
                    speed = (downloaded - last_downloaded) / time_diff
                    self.active_downloads[video_id].speed = speed
                    self.active_downloads[video_id].downloaded = downloaded
                    await self.update_db(video_id, downloaded=downloaded)
                    last_update_time = current_time
                    last_downloaded = downloaded
                    await self.broadcast_progress(video_id)
                
                await asyncio.sleep(self.progress_update_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"更新进度错误: {str(e)}")
    
    async def download_segment(self, video_id: str, url: str, output_path, segment: DownloadSegment, segment_index: int, semaphore: asyncio.Semaphore = None):
        """下载指定段，使用连接池和信号量控制并发"""
        max_retries = self.max_retries
        retries = 0
        backoff_time = 1  # 初始重试等待时间
        
        # 使用信号量控制并发量
        async with semaphore if semaphore else asyncio.nullcontext():
            while retries < max_retries:
                try:
                    # 检查是否被取消
                    if self.cancel_events.get(video_id):
                        return
                    
                    # 等待暂停事件
                    await self.pause_events[video_id].wait()
                    
                    # 计算实际起始位置
                    actual_start = segment.start + segment.downloaded
                    if actual_start > segment.end:
                        # 段已下载完成
                        segment.status = "completed"
                        return
                    
                    # 设置请求头
                    headers = {
                        "Range": f"bytes={actual_start}-{segment.end}",
                        "Connection": "keep-alive",  # 保持连接
                        "Accept-Encoding": "identity"  # 避免压缩导致的问题
                    }
                    
                    # 获取复用的HTTP客户端
                    client = await self.get_http_client(url)
                    
                    async with client.stream("GET", url, headers=headers) as response:
                        if response.status_code not in [200, 206]:
                            raise Exception(f"服务器返回错误状态码: {response.status_code}")
                        
                        segment.status = "downloading"
                        buffer = bytearray()
                        
                        # 使用aiofiles进行异步文件操作，提高性能
                        async with aiofiles.open(output_path, "r+b") as f:
                            await f.seek(actual_start)
                            
                            try:
                                async for chunk in response.aiter_bytes(self.chunk_size):
                                    # 检查是否被取消
                                    if self.cancel_events.get(video_id):
                                        return
                                    
                                    # 等待暂停事件
                                    await self.pause_events[video_id].wait()
                                    
                                    buffer.extend(chunk)
                                    if len(buffer) >= self.buffer_size:
                                        await f.write(buffer)
                                        segment.downloaded += len(buffer)
                                        buffer.clear()
                                
                                # 写入剩余buffer
                                if buffer:
                                    await f.write(buffer)
                                    segment.downloaded += len(buffer)
                                    
                            except asyncio.CancelledError:
                                # 处理取消请求
                                return
                        
                        # 段下载完成
                        segment.status = "completed"
                        logger.success(f"视频 {video_id} 段 {segment_index} 下载完成")
                        return
                except Exception as e:
                    retries += 1
                    # 使用指数退避策略进行重试
                    backoff_time = min(30, backoff_time * 1.5)  # 逐渐增加等待时间，但不超过30秒
                    logger.warning(f"视频 {video_id} 段 {segment_index} 下载失败 (尝试 {retries}/{max_retries}, 等待 {backoff_time:.1f}s): {str(e)}")
                    if retries >= max_retries:
                        segment.status = "error"
                        return
                    await asyncio.sleep(backoff_time)  # 使用指数退避等待
    
    async def simple_download(self, video_id: str, url: str, output_path, total_size: int, resume: bool = False):
        """使用单线程下载（用于不支持范围请求的服务器），优化性能和稳定性"""
        last_update_time = asyncio.get_event_loop().time()
        start_time = asyncio.get_event_loop().time()
        last_downloaded = 0
        downloaded = 0
        mode = "ab" if resume else "wb"
        
        if resume:
            downloaded = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            last_downloaded = downloaded
            
        await self.broadcast_progress(video_id)

        # 设置下载范围和优化的请求头
        headers = {
            "Connection": "keep-alive",
            "Accept-Encoding": "identity"  # 避免压缩导致的问题
        }
        
        if resume and downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
        
        # 重试机制
        max_retries = self.max_retries
        retries = 0
        backoff_time = 1  # 初始重试等待时间
        
        while retries <= max_retries:
            try:
                # 获取复用的HTTP客户端
                client = await self.get_http_client(url)
                
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code not in [200, 206]:
                        raise Exception(f"服务器返回错误状态码: {response.status_code}")
                    
                    # 使用异步文件操作提高性能
                    async with aiofiles.open(output_path, mode) as f:
                        buffer = bytearray()
                        try:
                            async for chunk in response.aiter_bytes(self.chunk_size):
                                # 检查是否被取消
                                if self.cancel_events.get(video_id):
                                    logger.info(f"检测到取消操作: {video_id}")
                                    try:
                                        os.remove(output_path)
                                    except:
                                        pass
                                    self.active_downloads[video_id].status = DownloadStatus.CANCELLED
                                    await self.update_db(video_id, status=DownloadStatus.CANCELLED)
                                    await self.broadcast_progress(video_id)
                                    return

                                # 检查下载ID是否仍然有效
                                if video_id not in self.active_downloads:
                                    raise Exception("下载任务已失效")

                                # 等待暂停事件
                                await self.pause_events[video_id].wait()
                                
                                buffer.extend(chunk)
                                if len(buffer) >= self.buffer_size:
                                    await f.write(buffer)
                                    downloaded += len(buffer)
                                    buffer.clear()
                                
                                # 计算下载速度并使用节流更新进度
                                current_time = asyncio.get_event_loop().time()
                                time_diff = current_time - last_update_time
                                if time_diff >= self.progress_update_interval:
                                    speed = (downloaded - last_downloaded) / time_diff
                                    self.active_downloads[video_id].speed = speed
                                    self.active_downloads[video_id].downloaded = downloaded
                                    
                                    # 优化数据库更新频率 - 只在进度变化明显时更新数据库
                                    progress_percent = downloaded / total_size * 100 if total_size > 0 else 0
                                    if progress_percent - (last_downloaded / total_size * 100 if total_size > 0 else 0) >= 1.0:
                                        # 进度变化超过1%才更新数据库
                                        await self.update_db(video_id, downloaded=downloaded)
                                        
                                    last_update_time = current_time
                                    last_downloaded = downloaded
                                    await self.broadcast_progress(video_id)
                            
                            # 写入剩余buffer
                            if buffer:
                                await f.write(buffer)
                                downloaded += len(buffer)

                            # 最后一次更新进度
                            self.active_downloads[video_id].downloaded = downloaded
                            await self.update_db(video_id, downloaded=downloaded)
                            await self.broadcast_progress(video_id)

                        except Exception as chunk_error:
                            raise Exception(f"下载数据时出错: {str(chunk_error)}")
                    
                    # 验证下载是否完整
                    if total_size > 0 and downloaded != total_size:
                        raise Exception(f"下载不完整: 已下载 {downloaded} 字节，总大小 {total_size} 字节")
                    
                    # 完成下载
                    self.active_downloads[video_id].status = DownloadStatus.COMPLETED
                    self.active_downloads[video_id].downloaded = total_size
                    completed_at = datetime.now()
                    await self.update_db(
                        video_id,
                        status=DownloadStatus.COMPLETED,
                        downloaded=total_size,
                        completed_at=completed_at
                    )
                    self.active_downloads[video_id].completed_at = completed_at
                    
                    # 计算带宽样本并存储
                    elapsed_time = asyncio.get_event_loop().time() - start_time
                    if elapsed_time > 0:
                        bandwidth = total_size / elapsed_time  # bytes/second
                        # 保留最新的10个样本
                        self.bandwidth_samples.append(bandwidth)
                        if len(self.bandwidth_samples) > 10:
                            self.bandwidth_samples.pop(0)
                    
                    await self.broadcast_progress(video_id)
                    
                    # 成功下载，不再重试
                    return
                    
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    raise Exception(f"单线程下载失败 (已重试 {retries-1} 次): {str(e)}")
                
                # 使用指数退避策略进行重试
                backoff_time = min(30, backoff_time * 1.5)
                logger.warning(f"视频 {video_id} 下载失败，等待 {backoff_time:.1f}s 后重试 ({retries}/{max_retries}): {str(e)}")
                await asyncio.sleep(backoff_time)

    async def pause_download(self, video_id: str):
        """暂停下载"""
        if video_id in self.pause_events:
            self.pause_events[video_id].clear()
            self.active_downloads[video_id].status = DownloadStatus.PAUSED
            await self.update_db(video_id, status=DownloadStatus.PAUSED)
            await self.broadcast_progress(video_id)
            return True
        return False

    async def resume_download(self, video_id: str):
        """继续下载"""
        if video_id in self.pause_events:
            self.pause_events[video_id].set()
            self.active_downloads[video_id].status = DownloadStatus.DOWNLOADING
            await self.update_db(video_id, status=DownloadStatus.DOWNLOADING)
            await self.broadcast_progress(video_id)
            return True
        return False

    async def retry_download(self, video_id: str):
        """重试下载"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM downloads WHERE video_id = ?",
                (video_id,)
            ) as cursor:
                download = await cursor.fetchone()
                if not download:
                    return False
                
                # 检查重试次数是否已达上限
                retry_count = download['retry_count'] + 1
                max_retries = download['max_retries'] if download['max_retries'] else 3
                
                if retry_count > max_retries:
                    # 更新错误信息
                    await db.execute(
                        "UPDATE downloads SET error_message = ? WHERE video_id = ?",
                        (f"已达到最大重试次数 ({max_retries})", video_id)
                    )
                    await db.commit()
                    if video_id in self.active_downloads:
                        self.active_downloads[video_id].error_message = f"已达到最大重试次数 ({max_retries})"
                    await self.broadcast_progress(video_id)
                    return False
                    
                # 更新下载状态为 downloading 并增加重试计数
                await db.execute(
                    "UPDATE downloads SET status = ?, error_message = NULL, retry_count = ? WHERE video_id = ?",
                    (DownloadStatus.DOWNLOADING, retry_count, video_id)
                )
                await db.commit()
                
                # 更新内存中的下载状态
                if video_id in self.active_downloads:
                    self.active_downloads[video_id].status = DownloadStatus.DOWNLOADING
                    self.active_downloads[video_id].error_message = None
                    self.active_downloads[video_id].retry_count = retry_count
                else:
                    # 如果active_downloads中不存在该ID，需要重新创建
                    self.active_downloads[video_id] = DownloadProgress(
                        video_id=video_id,
                        filename=download['filename'],
                        title=download['title'],
                        cover_url=download['cover_url'],
                        total_size=download['total_size'] or 0,
                        downloaded=download['downloaded'] or 0,
                        status=DownloadStatus.DOWNLOADING,
                        speed=0.0,
                        error_message=None,
                        url=download['url'],
                        created_at=download['created_at'],
                        completed_at=None,
                        retry_count=retry_count,
                        max_retries=max_retries
                    )
                    
                # 如果有暂停事件，设置它以继续下载
                if video_id in self.pause_events:
                    self.pause_events[video_id].set()
                else:
                    self.pause_events[video_id] = asyncio.Event()
                    self.pause_events[video_id].set()
                
                # 启动重试下载任务
                output_path = settings.DOWNLOAD_PATH / download["filename"]
                asyncio.create_task(
                    self.download_file(
                        video_id,
                        download["url"],
                        output_path,
                        resume=True
                    )
                )
                
                await self.broadcast_progress(video_id)
                return True

    async def cancel_download(self, video_id: str):
        """取消下载"""
        # 设置取消标志
        self.cancel_events[video_id] = True
        
        # 解除暂停以便取消操作能够进行
        if video_id in self.pause_events:
            self.pause_events[video_id].set()
            
        # 更新数据库中的状态
        await self.update_db(video_id, status=DownloadStatus.CANCELLED)
        
        # 更新内存中的状态
        if video_id in self.active_downloads:
            self.active_downloads[video_id].status = DownloadStatus.CANCELLED
            self.active_downloads[video_id].speed = 0  # 重置下载速度
            
            # 立即广播状态变化
            await self.broadcast_progress(video_id)
            
            # 等待一小段时间确保下载任务有机会响应取消事件
            await asyncio.sleep(0.5)
            
            # 检查任何可能仍在进行的下载线程是否需要强制终止
            # 此处可以添加更强力的终止策略
            
            return True
        
        return False

    async def check_existing_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """检查是否存在相同的下载"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM downloads WHERE video_id = ?",
                (video_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def delete_download(self, video_id: str) -> bool:
        """删除下载记录和文件"""
        try:
            # 先检查下载是否处于活跃状态，如果是，先尝试取消
            if video_id in self.active_downloads and self.active_downloads[video_id].status in ['downloading', 'paused', 'pending']:
                logger.info(f"删除前自动取消下载: {video_id}")
                await self.cancel_download(video_id)
                # 等待一会儿确保取消操作完成
                await asyncio.sleep(1)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取文件名
                async with db.execute(
                    "SELECT filename, status FROM downloads WHERE video_id = ?",
                    (video_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return False  # 记录不存在
                        
                    filename = row[0]
                    status = row[1]
                    
                    # 删除文件（如果是部分下载的文件也要删除）
                    file_path = settings.DOWNLOAD_PATH / filename
                    try:
                        if await aiofiles.os.path.exists(file_path):
                            await aiofiles.os.remove(file_path)
                            logger.info(f"删除文件成功: {file_path}")
                    except Exception as file_error:
                        logger.error(f"删除文件失败: {str(file_error)}")
                        # 继续删除数据库记录，即使文件删除失败
                
                # 删除数据库记录
                await db.execute("DELETE FROM downloads WHERE video_id = ?", (video_id,))
                await db.commit()
                logger.info(f"从数据库删除下载记录: {video_id}")

                # 清理内存中的记录
                if video_id in self.active_downloads:
                    del self.active_downloads[video_id]
                if video_id in self.pause_events:
                    self.pause_events[video_id].set()  # 解除暂停
                    del self.pause_events[video_id]
                if video_id in self.cancel_events:
                    del self.cancel_events[video_id]
                # 清理速度计算数据
                if hasattr(self, 'speedSmoother') and self.speedSmoother:
                    self.speedSmoother.clearHistory(video_id)

                return True
        except Exception as e:
            logger.error(f"删除下载失败: {str(e)}")
            return False

    async def start_download(self, video_id: str, force: bool = False):
        """
        启动下载
        :param video_id: 视频ID
        :param force: 是否强制重新下载已存在的视频
        """
        # 先检查是否有相同ID的下载记录
        existing_download = await self.check_existing_download(video_id)
        
        if existing_download and not force:
                return {
                    "status": "warning",
                "message": "视频已在下载列表中",
                    "existing_download": existing_download
                }
        elif existing_download and force:
            # 删除现有下载
            await self.delete_download(video_id)
            
        try:
            # 获取视频详情
            video_detail = await self.video_service.get_video_detail(video_id)
            if not video_detail:
                return {"status": "error", "message": "视频不存在或获取失败"}
            
            # 选择最佳的下载URL
            best_url = self._get_best_stream_url(video_detail.stream_urls)
            if not best_url:
                return {"status": "error", "message": "未找到有效的下载链接"}
            
            # 优先使用副标题作为文件名，如果没有副标题则使用标题
            if video_detail.subtitle:
                filename = self._sanitize_filename(video_detail.subtitle)
            else:
                filename = self._sanitize_filename(video_detail.title)
            
            # 确保文件名唯一
            filename = f"{video_id}_{filename}.mp4"
            
            # 创建下载记录
            file_path = settings.DOWNLOAD_PATH / filename
            
            # 写入数据库
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "INSERT OR REPLACE INTO downloads (video_id, title, filename, cover_url, url, status, total_size, downloaded, retry_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        video_id, 
                        video_detail.title, 
                        filename, 
                        video_detail.cover_url, 
                        best_url, 
                        DownloadStatus.PENDING,
                        0,
                        0,
                        0
                    )
                )
                await conn.commit()
            
            # 创建下载进度对象
            self.active_downloads[video_id] = DownloadProgress(
                video_id=video_id,
                filename=filename,
                title=video_detail.title,
                cover_url=video_detail.cover_url,
                url=best_url,
                total_size=0,
                downloaded=0,
                status=DownloadStatus.PENDING,
                speed=0.0,
                created_at=datetime.now()
            )
            
            # 广播初始状态
            await self.broadcast_progress(video_id)
            
            # 启动下载任务
            asyncio.create_task(self.download_file(video_id, best_url, file_path))
            
            return {"status": "success", "message": "已开始下载"}
        except Exception as e:
            logger.error(f"启动下载失败: {str(e)}")
            return {"status": "error", "message": f"启动下载失败: {str(e)}"}

    def _get_best_stream_url(self, stream_urls):
        """获取最佳视频流URL"""
        if not stream_urls:
            return None
            
        # 优先选择高质量流
        quality_priority = {"1080p": 1, "720p": 2, "480p": 3, "360p": 4, "240p": 5}
        
        # 由于stream_urls是VideoStreamUrl对象列表，我们需要通过属性访问
        sorted_streams = sorted(
            stream_urls, 
            key=lambda x: quality_priority.get(x.quality.lower(), 999)
        )
        
        return sorted_streams[0].url if sorted_streams else None
    
    def _sanitize_filename(self, filename):
        """处理文件名，移除非法字符"""
        # 替换非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:196] + ext
            
        return filename

    async def get_http_client(self, url: str):
        """获取或创建HTTP客户端，实现连接池复用"""
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # 检查是否已有相应域名的连接池
        if domain in self.http_clients:
            return self.http_clients[domain]
            
        # 设置httpx客户端选项
        client_options = {
            'timeout': httpx.Timeout(self.timeout, connect=self.timeout),
            'follow_redirects': True,
            'verify': False,  # 禁用SSL验证以处理特殊情况
            'limits': httpx.Limits(
                max_connections=self.connection_pool_size,
                max_keepalive_connections=self.connection_pool_size,
                keepalive_expiry=60  # 连接保持时间(秒)
            )
        }
        
        # 设置代理
        if settings.USE_DOWNLOAD_PROXY and settings.DOWNLOAD_PROXY_URL:
            client_options['proxies'] = settings.DOWNLOAD_PROXY_URL
            
        # 创建新的客户端
        client = httpx.AsyncClient(**client_options)
        self.http_clients[domain] = client
        return client
        
    async def close_http_clients(self):
        """关闭所有HTTP客户端连接"""
        for domain, client in self.http_clients.items():
            try:
                await client.aclose()
            except Exception as e:
                logger.error(f"关闭HTTP客户端失败 ({domain}): {str(e)}")
        self.http_clients = {}


# 创建下载管理器实例
download_manager = DownloadManager() 
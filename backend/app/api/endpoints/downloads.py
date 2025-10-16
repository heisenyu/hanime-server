from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from app.services.download_service import download_manager
from app.models.download import DownloadRequest, DownloadAction
from typing import List, Dict, Any, Optional
from app.config import settings, logger
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.on_event("startup")
async def startup():
    """应用启动时初始化下载管理器"""
    await download_manager.init_db()
    logger.info("初始化数据库成功")
    await download_manager.load_downloads()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接处理，用于实时更新下载进度"""
    await websocket.accept()
    download_manager.websocket_connections.add(websocket)
    try:
        # 连接建立后发送现有下载状态
        for video_id, download in download_manager.active_downloads.items():
            await download_manager.broadcast_progress(video_id)
            
        # 保持连接，直到客户端断开
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket连接断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        download_manager.websocket_connections.remove(websocket)


@router.get("/history")
async def get_download_history() -> List[Dict[str, Any]]:
    """获取下载历史记录"""
    return await download_manager.get_download_history()


@router.post("/start")
async def start_download(download_request: DownloadRequest):
    """开始下载视频"""
    return await download_manager.start_download(
        download_request.video_id,
        download_request.force
    )


@router.post("/action")
async def handle_download_action(action: DownloadAction):
    """处理下载操作(暂停/继续/取消/重试/删除)"""
    video_id = action.video_id
    action_type = action.action.lower()
    result = {"status": "error", "message": "无效的操作"}
    
    if action_type == "pause":
        success = await download_manager.pause_download(video_id)
        result = {"status": "success" if success else "error", "message": "暂停操作处理完成" if success else "操作失败"}
    elif action_type == "resume":
        success = await download_manager.resume_download(video_id)
        result = {"status": "success" if success else "error", "message": "继续操作处理完成" if success else "操作失败"}
    elif action_type == "cancel":
        success = await download_manager.cancel_download(video_id)
        result = {"status": "success" if success else "error", "message": "取消操作处理完成" if success else "操作失败"}
    elif action_type == "retry":
        success = await download_manager.retry_download(video_id)
        result = {"status": "success" if success else "error", "message": "重试操作处理完成" if success else "操作失败"}
    elif action_type == "delete":
        success = await download_manager.delete_download(video_id)
        result = {"status": "success" if success else "error", "message": "删除操作处理完成" if success else "操作失败"}
    
    return result


@router.get("/file/{video_id}")
async def get_downloaded_file(video_id: str):
    """获取已下载的文件"""
    # 检查视频是否存在且已下载完成
    download_info = await download_manager.check_existing_download(video_id)
    if not download_info:
        return {"status": "error", "message": "下载记录不存在"}
    
    if download_info['status'] != 'completed':
        return {"status": "error", "message": "下载尚未完成"}
    
    file_path = settings.DOWNLOAD_PATH / download_info['filename']
    if not os.path.exists(file_path):
        return {"status": "error", "message": "文件不存在"}
    
    return FileResponse(
        path=file_path,
        filename=download_info['filename'],
        media_type='video/mp4'
    )


@router.get("/cover/{video_id}")
async def get_cover(video_id: str):
    """
    获取本地封面图片
    如果本地不存在，则实时获取视频详情并下载封面
    """
    cover_filename = f"{video_id}.jpg"
    cover_path = settings.COVER_PATH / cover_filename
    
    # 如果本地封面不存在，尝试下载
    if not cover_path.exists():
        logger.info(f"本地封面不存在，尝试下载视频 {video_id} 的封面")
        
        # 获取视频详情
        from app.services.video_service import VideoService
        video_service = VideoService()
        
        try:
            video_detail = await video_service.get_video_detail(video_id)
            if video_detail and video_detail.cover_url:
                # 下载封面
                await download_manager.download_cover(video_id, video_detail.cover_url)
                
                # 再次检查是否下载成功
                if not cover_path.exists():
                    raise HTTPException(status_code=404, detail="封面下载失败")
            else:
                raise HTTPException(status_code=404, detail="无法获取视频信息")
        except Exception as e:
            logger.error(f"获取封面失败: {str(e)}")
            raise HTTPException(status_code=404, detail=f"获取封面失败: {str(e)}")
    
    return FileResponse(
        path=cover_path,
        media_type='image/jpeg'
    ) 
<!-- 评论组件 -->
<template>
  <div class="comments-container">
    <div class="comments-header">
      <div class="comment-count">评论 <span class="comment-number">{{ commentCount }}</span></div>
      <div class="comment-sort">
        <span class="sort-label">排序方式:</span>
        <el-dropdown trigger="click" @command="handleSortChange">
          <span class="el-dropdown-link">
            {{ currentSort }} <i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="popular">最热</el-dropdown-item>
              <el-dropdown-item command="latest">最新</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 评论列表 -->
    <div class="comments-list" v-if="comments.length > 0">
      <div v-for="comment in comments" :key="comment.comment_id" class="comment-item">
        <!-- 评论主体 -->
        <div class="comment-main">
          <div class="comment-avatar">
            <img :src="comment.user_avatar || defaultAvatarUrl" alt="用户头像"
                 referrerpolicy="no-referrer" loading="lazy" @error="handleImageError"/>
          </div>
          <div class="comment-content">
            <div class="comment-user">
              <span class="username">{{ comment.username }}</span>
              <span class="comment-time">{{ comment.comment_time }}</span>
            </div>
            <div class="comment-text">{{ comment.comment_content }}</div>
            <div class="comment-actions">
              <div class="comment-like">
                <svg class="thumb-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
                  <path d="M885.9 533.7c16.8-22.2 26.1-49.4 26.1-77.7 0-44.9-25.1-87.4-65.5-111.1a67.67 67.67 0 0 0-34.3-9.3H572.4l6-122.9c1.4-29.7-9.1-57.9-29.5-79.4-20.5-21.5-48.1-33.4-77.9-33.4-52 0-98 35-111.8 85.1l-85.9 311H144c-17.7 0-32 14.3-32 32v364c0 17.7 14.3 32 32 32h601.3c9.2 0 18.2-1.8 26.5-5.4 47.6-20.3 78.3-66.8 78.3-118.4 0-12.6-1.8-25-5.4-37 16.8-22.2 26.1-49.4 26.1-77.7 0-12.6-1.8-25-5.4-37 16.8-22.2 26.1-49.4 26.1-77.7-0.2-12.6-2-25.1-5.6-37.1zM184 852V568h81v284h-81z m636.4-353l-21.9 19 13.9 25.4c4.6 8.4 6.9 17.6 6.9 27.3 0 16.5-7.2 32.2-19.6 43l-21.9 19 13.9 25.4c4.6 8.4 6.9 17.6 6.9 27.3 0 16.5-7.2 32.2-19.6 43l-21.9 19 13.9 25.4c4.6 8.4 6.9 17.6 6.9 27.3 0 22.4-13.2 42.6-33.6 51.8H329V564.8l99.5-360.5c5.2-18.9 22.5-32.2 42.2-32.3 7.6 0 15.1 2.2 21.1 6.7 9.9 7.4 15.2 18.6 14.6 30.5l-9.6 198.4h314.4C829 418.5 840 436.9 840 456c0 16.5-7.2 32.1-19.6 43z" fill="#ec4899"></path>
                </svg>
                <span class="like-count">{{ comment.like_count || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 查看回复 -->
        <div class="view-replies" v-if="comment.reply_count > 0" @click="loadReplies(comment.comment_id)">
          <span>{{
              activeRepliesId === comment.comment_id ? '收起回复' : `查看 ${comment.reply_count} 条回复`
            }}</span>
          <el-icon>
            <component :is="activeRepliesId === comment.comment_id ? 'ArrowUp' : 'ArrowDown'" />
          </el-icon>
        </div>

        <!-- 回复列表 -->
        <div class="replies-list" v-if="comment.comment_id === activeRepliesId && replies.length > 0">
          <!-- 回复排序控制 -->
          <div class="replies-sort-control">
            <span class="replies-sort-label">排序方式:</span>
            <el-dropdown trigger="click" @command="handleRepliesSortChange">
              <span class="el-dropdown-link">
                {{ repliesSort }} <i class="el-icon-arrow-down el-icon--right"></i>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="popular">最热</el-dropdown-item>
                  <el-dropdown-item command="latest">最新</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          
          <div v-for="reply in replies" :key="reply.username + reply.reply_time" class="reply-item">
            <div class="reply-avatar">
              <img :src="reply.user_avatar || defaultAvatarUrl" alt="用户头像"
                   referrerpolicy="no-referrer" loading="lazy" @error="handleImageError"/>
            </div>
            <div class="reply-content">
              <div class="reply-user">
                <span class="username">{{ reply.username }}</span>
                <span class="reply-time">{{ reply.reply_time }}</span>
              </div>
              <div class="reply-text">{{ reply.reply_content }}</div>
              <div class="reply-actions">
                <div class="reply-like">
                  <svg class="thumb-icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="14" height="14">
                    <path d="M885.9 533.7c16.8-22.2 26.1-49.4 26.1-77.7 0-44.9-25.1-87.4-65.5-111.1a67.67 67.67 0 0 0-34.3-9.3H572.4l6-122.9c1.4-29.7-9.1-57.9-29.5-79.4-20.5-21.5-48.1-33.4-77.9-33.4-52 0-98 35-111.8 85.1l-85.9 311H144c-17.7 0-32 14.3-32 32v364c0 17.7 14.3 32 32 32h601.3c9.2 0 18.2-1.8 26.5-5.4 47.6-20.3 78.3-66.8 78.3-118.4 0-12.6-1.8-25-5.4-37 16.8-22.2 26.1-49.4 26.1-77.7 0-12.6-1.8-25-5.4-37 16.8-22.2 26.1-49.4 26.1-77.7-0.2-12.6-2-25.1-5.6-37.1zM184 852V568h81v284h-81z m636.4-353l-21.9 19 13.9 25.4c4.6 8.4 6.9 17.6 6.9 27.3 0 16.5-7.2 32.2-19.6 43l-21.9 19 13.9 25.4c4.6 8.4 6.9 17.6 6.9 27.3 0 16.5-7.2 32.2-19.6 43l-21.9 19 13.9 25.4c4.6 8.4 6.9 17.6 6.9 27.3 0 22.4-13.2 42.6-33.6 51.8H329V564.8l99.5-360.5c5.2-18.9 22.5-32.2 42.2-32.3 7.6 0 15.1 2.2 21.1 6.7 9.9 7.4 15.2 18.6 14.6 30.5l-9.6 198.4h314.4C829 418.5 840 436.9 840 456c0 16.5-7.2 32.1-19.6 43z" fill="#ec4899"></path>
                  </svg>
                  <span class="like-count">{{ reply.like_count || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载更多评论 -->
    <div class="load-more" v-if="hasMoreComments">
      <el-button link @click="loadMoreComments">查看更多评论</el-button>
    </div>

    <!-- 暂无评论 -->
    <div class="no-comments" v-if="comments.length === 0 && !loadingComments">
      <el-icon><ChatDotRound /></el-icon>
      <p>暂无评论</p>
    </div>

    <!-- 评论加载中 -->
    <div class="loading-comments" v-if="loadingComments">
      <el-skeleton :rows="3" animated/>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue';
import { VideoApi } from '../api/video';
import { VideoComment, CommentReply } from '../types/video';
import { ArrowUp, ArrowDown, ChatDotRound } from '@element-plus/icons-vue';
import defaultAvatar from '../assets/default-avatar.svg';

export default defineComponent({
  name: 'VideoComments',
  components: {
    ArrowUp,
    ArrowDown,
    ChatDotRound
  },
  props: {
    videoId: {
      type: String,
      required: true
    },
    showDebugInfo: {
      type: Boolean,
      default: false
    }
  },
  emits: ['debug-log', 'comment-count-updated'],
  setup(props, { emit }) {
    const commentCount = ref(0);
    const comments = ref<VideoComment[]>([]);
    const replies = ref<CommentReply[]>([]);
    const loadingComments = ref(false);
    const hasMoreComments = ref(false);
    const currentSort = ref('最热');
    const repliesSort = ref('最热'); // 子评论排序方式
    const activeRepliesId = ref('');
    
    // 默认头像URL
    const defaultAvatarUrl = ref(defaultAvatar);
    
    // 处理头像加载错误
    const handleImageError = (event: Event) => {
      const imgElement = event.target as HTMLImageElement;
      imgElement.src = defaultAvatar;
    };
    
    // 缓存已加载的回复
    const repliesCache = ref<{[key: string]: CommentReply[]}>({});
    // 原始评论数据（未排序）
    const originalComments = ref<VideoComment[]>([]);
    // 原始回复数据（未排序）
    const originalReplies = ref<{[key: string]: CommentReply[]}>({});

    // 调试日志函数
    const addDebugLog = (message: string) => {
      if (props.showDebugInfo) {
        emit('debug-log', message);
      }
    };
    
    // 解析评论时间字符串为日期对象
    const parseCommentTime = (timeString: string | undefined): Date => {
      if (!timeString) return new Date(0); // 默认返回最早时间
      
      const now = new Date();
      const units = {
        '年前': { unit: 'year', value: 365 * 24 * 60 * 60 * 1000 },
        '個月前': { unit: 'month', value: 30 * 24 * 60 * 60 * 1000 },
        '週前': { unit: 'week', value: 7 * 24 * 60 * 60 * 1000 },
        '天前': { unit: 'day', value: 24 * 60 * 60 * 1000 },
        '小時前': { unit: 'hour', value: 60 * 60 * 1000 },
        '分鐘前': { unit: 'minute', value: 60 * 1000 },
        '秒前': { unit: 'second', value: 1000 }
      };
      
      // 匹配数字和单位
      for (const [unit, { value }] of Object.entries(units)) {
        if (timeString.includes(unit)) {
          const number = parseInt(timeString.split(unit)[0]);
          if (!isNaN(number)) {
            return new Date(now.getTime() - (number * value));
          }
        }
      }
      
      // 如果无法解析，返回当前时间
      return now;
    };
    
    // 排序评论
    const sortComments = (sortType: string) => {
      if (!originalComments.value.length) return;
      
      // 清空当前评论列表，避免重复
      comments.value = [];
      
      // 确保每个评论有唯一标识符
      const commentsWithIds = originalComments.value.map((comment, index) => {
        // 如果评论没有ID，使用索引作为ID
        if (!comment.comment_id) {
          return { ...comment, comment_id: `comment-${index}` };
        }
        return comment;
      });
      
      // 创建一个新数组进行排序，避免修改原始数据
      let sortedComments;
      
      if (sortType === '最新') {
        // 按时间排序（从新到旧）
        sortedComments = [...commentsWithIds].sort((a, b) => {
          const dateA = parseCommentTime(a.comment_time);
          const dateB = parseCommentTime(b.comment_time);
          return dateB.getTime() - dateA.getTime();
        });
      } else {
        // 最热排序（使用原始顺序）
        sortedComments = [...commentsWithIds];
      }
      
      // 确保没有重复项
      const uniqueCommentIds = new Set();
      const uniqueComments = [];
      
      for (const comment of sortedComments) {
        if (comment.comment_id && !uniqueCommentIds.has(comment.comment_id)) {
          uniqueCommentIds.add(comment.comment_id);
          uniqueComments.push(comment);
        }
      }
      
      // 更新评论列表
      comments.value = uniqueComments;
    };

    // 获取视频评论
    const fetchComments = async () => {
      if (!props.videoId) return;

      try {
        loadingComments.value = true;
        comments.value = []; // 清空当前评论列表，避免可能的重复显示
        
        const response = await VideoApi.getVideoComments(props.videoId);

        if (response && response.length > 0) {
          // 添加唯一标识符
          const processedResponse = response.map((comment, index) => {
            if (!comment.comment_id) {
              return { ...comment, comment_id: `comment-${index}` };
            }
            return comment;
          });
          
          // 保存原始评论数据
          originalComments.value = processedResponse;
          // 应用当前排序
          sortComments(currentSort.value);
          commentCount.value = response.length;
          hasMoreComments.value = response.length >= 20; // 假设每页20条评论
          
          // 更新父组件中的评论数
          emit('comment-count-updated', response.length);
          
          addDebugLog(`成功加载 ${response.length} 条评论，排序方式: ${currentSort.value}`);
        } else {
          originalComments.value = [];
          comments.value = [];
          hasMoreComments.value = false;
          
          // 更新父组件中的评论数为0
          emit('comment-count-updated', 0);
          
          addDebugLog('没有找到评论');
        }
      } catch (err) {
        console.error('获取评论失败:', err);
        addDebugLog(`获取评论失败: ${err}`);
        
        // 更新父组件中的评论数为0（出错时）
        emit('comment-count-updated', 0);
      } finally {
        loadingComments.value = false;
      }
    };

    // 加载更多评论
    const loadMoreComments = async () => {
      // 这里应该实现分页加载逻辑
      console.log('加载更多评论');
    };

    // 排序回复
    const sortReplies = (sortType: string, commentId: string) => {
      if (!originalReplies.value[commentId] || !originalReplies.value[commentId].length) return;
      
      // 清空当前回复列表，避免重复
      replies.value = [];
      
      // 确保每个回复有唯一标识符
      const repliesWithIds = originalReplies.value[commentId].map((reply, index) => {
        // 如果回复没有唯一标识，使用用户名+时间+索引作为标识
        const replyId = `${reply.username}-${reply.reply_time}-${index}`;
        return { ...reply, reply_id: replyId };
      });
      
      // 创建一个新数组进行排序
      let sortedReplies;
      
      if (sortType === '最新') {
        // 按时间排序（从新到旧）
        sortedReplies = [...repliesWithIds].sort((a, b) => {
          const dateA = parseCommentTime(a.reply_time);
          const dateB = parseCommentTime(b.reply_time);
          return dateB.getTime() - dateA.getTime();
        });
      } else {
        // 最热排序（使用原始顺序或按点赞数排序）
        sortedReplies = [...repliesWithIds].sort((a, b) => {
          const likeA = a.like_count || 0;
          const likeB = b.like_count || 0;
          return likeB - likeA;
        });
      }
      
      // 更新回复列表
      replies.value = sortedReplies;
    };
    
    // 处理回复排序变更
    const handleRepliesSortChange = (command: string) => {
      // 如果排序方式没有变化，不做处理
      const newSort = command === 'latest' ? '最新' : '最热';
      if (newSort === repliesSort.value) return;
      
      // 更新排序方式
      repliesSort.value = newSort;
      
      // 应用排序
      if (activeRepliesId.value && originalReplies.value[activeRepliesId.value]) {
        sortReplies(repliesSort.value, activeRepliesId.value);
        
        addDebugLog(`回复排序已更改为: ${repliesSort.value}, 共 ${replies.value.length} 条回复`);
      }
    };
    
    // 加载评论回复
    const loadReplies = async (commentId: string) => {
      // 如果点击的是当前已展开的回复，则关闭它
      if (activeRepliesId.value === commentId) {
        activeRepliesId.value = '';
        replies.value = [];
        return;
      }
      
      // 如果已经缓存了该评论的回复，直接使用缓存
      if (repliesCache.value[commentId]) {
        // 使用原始数据并应用当前排序
        if (originalReplies.value[commentId]) {
          activeRepliesId.value = commentId;
          sortReplies(repliesSort.value, commentId);
          return;
        }
        
        replies.value = repliesCache.value[commentId];
        activeRepliesId.value = commentId;
        return;
      }

      try {
        const response = await VideoApi.getCommentReplies(commentId);

        if (response && response.length > 0) {
          // 添加唯一标识符
          const processedResponse = response.map((reply, index) => {
            const replyId = `${reply.username}-${reply.reply_time}-${index}`;
            return { ...reply, reply_id: replyId };
          });
          
          // 保存到缓存和原始数据
          repliesCache.value[commentId] = processedResponse;
          originalReplies.value[commentId] = processedResponse;
          
          // 应用排序
          activeRepliesId.value = commentId;
          sortReplies(repliesSort.value, commentId);
        } else {
          replies.value = [];
          // 缓存空结果，避免重复请求
          repliesCache.value[commentId] = [];
          originalReplies.value[commentId] = [];
        }
      } catch (err) {
        console.error('获取回复失败:', err);
      }
    };

    // 处理排序变更
    const handleSortChange = (command: string) => {
      // 如果排序方式没有变化，不做处理
      const newSort = command === 'latest' ? '最新' : '最热';
      if (newSort === currentSort.value) return;
      
      // 更新排序方式
      currentSort.value = newSort;
      
      // 应用排序而不重新加载评论
      if (originalComments.value.length > 0) {
        sortComments(currentSort.value);
        // 添加调试信息
        addDebugLog(`评论排序已更改为: ${currentSort.value}, 共 ${comments.value.length} 条评论`);
      } else {
        // 如果还没有评论数据，则加载评论
        fetchComments();
      }
    };

    onMounted(() => {
      fetchComments();
    });

    // 监听videoId变化，重新加载评论
    watch(() => props.videoId, (newId) => {
      if (newId) {
        // 重置评论相关状态
        repliesCache.value = {};
        replies.value = [];
        activeRepliesId.value = '';
        comments.value = [];
        originalComments.value = [];
        
        // 获取新视频评论
        fetchComments();
      }
    });

    return {
      commentCount,
      comments,
      replies,
      loadingComments,
      hasMoreComments,
      currentSort,
      repliesSort,
      activeRepliesId,
      fetchComments,
      loadMoreComments,
      loadReplies,
      handleSortChange,
      handleRepliesSortChange,
      defaultAvatarUrl,
      handleImageError
    };
  }
});
</script>

<style scoped>
.comments-container {
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}

.comments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.comment-count {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
}

.comment-number {
  color: var(--secondary-color);
  font-weight: 600;
  margin-left: 5px;
}

.comment-sort {
  font-size: 14px;
  color: var(--text-secondary-color);
  display: flex;
  align-items: center;
}

.sort-label {
  margin-right: 8px;
}

.el-dropdown-link {
  color: var(--text-secondary-color);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comment-item {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 15px;
}

.comment-main {
  display: flex;
  gap: 12px;
}

.comment-avatar img,
.reply-avatar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
}

.comment-content,
.reply-content {
  flex: 1;
}

.comment-user,
.reply-user {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.username {
  font-weight: 500;
  margin-right: 8px;
  color: var(--text-color);
}

.comment-time,
.reply-time {
  font-size: 12px;
  color: var(--text-secondary-color);
}

.comment-text,
.reply-text {
  margin-bottom: 8px;
  line-height: 1.5;
  word-break: break-word;
  color: var(--text-color);
}

.comment-actions,
.reply-actions {
  display: flex;
  gap: 15px;
}

.comment-like,
.comment-reply,
.reply-like {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--text-secondary-color);
  transition: color 0.2s;
}

.thumb-icon {
  margin-right: 5px;
  transition: color 0.2s;
  vertical-align: middle;
}

.comment-like:hover,
.comment-reply:hover,
.reply-like:hover {
  color: var(--primary-color);
}

.like-count {
  line-height: 1;
  display: inline-block;
  vertical-align: middle;
  font-size: 14px;
  color: var(--text-secondary-color);
}

.view-replies {
  margin-top: 10px;
  margin-left: 52px;
  color: var(--secondary-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
}

.replies-list {
  margin-top: 15px;
  margin-left: 52px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.replies-sort-control {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.replies-sort-label {
  font-size: 13px;
  color: var(--text-secondary-color);
  margin-right: 8px;
}

.reply-item {
  display: flex;
  gap: 10px;
}

.reply-avatar img {
  width: 30px;
  height: 30px;
}

.load-more {
  text-align: center;
  margin-top: 20px;
}

.no-comments {
  text-align: center;
  padding: 30px 0;
  color: var(--text-secondary-color);
}

.no-comments i {
  font-size: 40px;
  margin-bottom: 10px;
}

.loading-comments {
  padding: 10px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .comments-container {
    padding: 12px;
  }
  
  .comment-avatar img {
    width: 36px;
    height: 36px;
  }
  
  .reply-avatar img {
    width: 26px;
    height: 26px;
  }
}

@media (max-width: 480px) {
  .comments-container {
    padding: 10px;
  }
  
  .comment-avatar img {
    width: 32px;
    height: 32px;
  }
  
  .reply-avatar img {
    width: 24px;
    height: 24px;
  }
  
  .comment-text,
  .reply-text {
    font-size: 14px;
  }
  
  .view-replies {
    margin-left: 42px;
    font-size: 13px;
  }
  
  .replies-list {
    margin-left: 42px;
  }
}
</style> 
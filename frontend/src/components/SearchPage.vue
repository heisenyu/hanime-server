<template>
  <div class="page-container">
    <!-- 搜索区域 -->
    <div class="search-header">
      <div class="search-container">
        <el-input
            v-model="searchQuery"
            placeholder="今天想看点什么呢"
            class="search-input"
            @keyup.enter="handleSearch"
            clearable
        >
        </el-input>

        <el-button type="primary" class="search-button" @click="handleSearch" :loading="isLoading">
          <el-icon>
            <Search/>
          </el-icon>
        </el-button>

        <el-button class="filter-button" @click="showAdvancedSearch = true">
          <el-icon>
            <Filter/>
          </el-icon>
        </el-button>
      </div>
    </div>

    <!-- 高级搜索抽屉 -->
    <el-dialog
        v-model="showAdvancedSearch"
        title="高级搜索"
        width="80%"
        custom-class="advanced-search-dialog"
        :show-close="true"
        :close-on-click-modal="true"
        :close-on-press-escape="true"
    >
      <div class="advanced-search-container">
        <!-- 类型选择 -->
        <div class="filter-section">
          <h3 class="section-title">类型</h3>
          <div class="filter-options">
            <el-tag
                v-for="type in searchCombination.video_types"
                :key="type"
                :class="{ 'active': selectedGenre === type }"
                @click="toggleGenre(type)"
                class="filter-option-tag"
            >
              {{ type }}
            </el-tag>
          </div>
        </div>

        <!-- 排序方式 -->
        <div class="filter-section">
          <h3 class="section-title">排序方式</h3>
          <div class="filter-options">
            <el-tag
                v-for="sort in searchCombination.sort"
                :key="sort"
                :class="{ 'active': selectedSort === sort }"
                @click="setSortBy(sort)"
                class="filter-option-tag"
            >
              {{ sort }}
            </el-tag>
          </div>
        </div>

        <!-- 标签选择 -->
        <div class="filter-section">
          <h3 class="section-title">标签</h3>
          <div class="tag-filter-header">
            <el-switch
                v-model="broadSearch"
                active-text="广泛配对"
                inactive-text="精准匹配"
                class="match-switch"
            />
            <div class="match-tip">{{ broadSearch ? '较多结果，较不精准。配对所有包含任何一个选择的标签的影片' : '较精准结果，较少数量。仅匹配包含全部所选标签的影片' }}</div>
          </div>

          <el-tabs type="card" class="tag-tabs" ref="tagTabs">
            <el-tab-pane v-for="(tagList, category) in searchCombination.tags" :key="category" :label="category">
              <div class="tag-options">
                <el-tag
                    v-for="tag in tagList"
                    :key="tag"
                    :class="{ 'active': selectedTags[tag] }"
                    @click="toggleTag(tag)"
                    effect="dark"
                    class="tag-item"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 发布日期 -->
        <div class="filter-section">
          <h3 class="section-title">
            发布日期
            <el-tooltip content="重置日期" placement="top" effect="light">
              <el-button
                  class="reset-date-button"
                  @click="clearDateFilter"
                  circle
                  plain
                  size="small"
              >
              <el-icon><RefreshRight /></el-icon>
              </el-button>
            </el-tooltip>
          </h3>
          <div class="date-selector">
            <div class="year-month-selector">
              <div class="year-selector">
                <el-select v-model="selectedYear" placeholder="选择年份" class="year-select">
                  <el-option
                      v-for="year in availableYears"
                      :key="year"
                      :label="`${year}年`"
                      :value="year"
                  />
                </el-select>
              </div>
              <div class="month-selector">
                <el-select v-model="selectedMonth" placeholder="选择月份" class="month-select">
                  <el-option
                      v-for="month in 12"
                      :key="month"
                      :label="`${month.toString().padStart(2, '0')}月`"
                      :value="month"
                  />
                </el-select>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" @click="applyAdvancedSearch">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 活跃过滤器标签 -->
    <div class="active-filters" v-if="hasActiveFilters">
      <div class="filter-tags">
        <el-tag
            v-if="selectedGenre"
            class="filter-tag"
            closable
            @close="clearGenre"
            type="info"
            effect="dark"
        >
          类型: {{ selectedGenre }}
        </el-tag>

        <el-tag
            v-for="tag in getSelectedTagsArray()"
            :key="tag"
            class="filter-tag"
            closable
            @close="removeTag(tag)"
            type="info"
            effect="dark"
        >
          {{ tag }}
        </el-tag>

        <el-tag
            v-if="selectedSort"
            class="filter-tag"
            closable
            @close="selectedSort = ''; handleSearch()"
            type="info"
            effect="dark"
        >
          排序: {{ selectedSort }}
        </el-tag>

        <el-tag
            v-if="selectedYear"
            class="filter-tag"
            closable
            @close="clearDateFilter(); handleSearch()"
            type="info"
            effect="dark"
        >
          {{ selectedYear }}年{{ selectedMonth ? selectedMonth + '月' : '' }}
        </el-tag>
      </div>

      <el-button size="small" @click="resetFilters(); handleSearch()">清除全部</el-button>
    </div>

    <!-- 搜索结果 -->
    <div v-if="isLoading && !hasResults" class="loading-container">
      <el-skeleton :rows="5" animated/>
    </div>

    <div v-if="showNoResults" class="search-hint">
      <p>没有找到相关视频</p>
    </div>

    <div v-if="hasResults" class="search-results-container">
      <h2 class="results-title" v-if="searchQuery || hasActiveFilters">
        搜索结果
      </h2>

      <!-- 基础视频结果 - 长图样式 -->
      <div v-if="searchResults.basic_videos && searchResults.basic_videos.length" class="video-grid-basic">
        <video-card
            v-for="video in searchResults.basic_videos"
            :key="video.video_id"
            :video="video"
            :custom-class="'video-card basic-video-card'"
            thumbnail-class="portrait"
            :show-play-icon="true"
            @click="goToVideo(video.video_id)"
        />
      </div>

      <!-- 详细视频结果 - 宽图样式 -->
      <div v-if="searchResults.detailed_videos && searchResults.detailed_videos.length" class="video-grid-detailed">
        <video-card
            v-for="video in searchResults.detailed_videos"
            :key="video.video_id"
            :video="video"
            :custom-class="'video-card wide-video-card'"
            thumbnail-class="landscape"
            :single-line-title="true"
            :show-play-icon="true"
            @click="goToVideo(video.video_id)"
        />
      </div>

      <!-- 无限加载 -->
      <div class="infinite-loading" v-if="hasMore" ref="loadMoreTrigger">
        <el-icon class="is-loading" v-if="loadingMore">
          <Loading/>
        </el-icon>
        <span v-else>加载更多</span>
      </div>
    </div>

    <div class="search-hint" v-if="!isLoading && !hasResults">
      <p>请输入关键词进行搜索</p>
    </div>


    <!-- 返回顶部按钮 -->
    <el-backtop :right="20" :bottom="20"></el-backtop>
  </div>
</template>

<script lang="ts">
import {defineComponent, ref, reactive, onMounted, watch, computed, nextTick, onUnmounted} from 'vue';
import {useRouter, useRoute} from 'vue-router';
import {Search, Filter, Back, Loading, Close, RefreshRight} from '@element-plus/icons-vue';
import {ElMessage} from 'element-plus';
import VideoCard from './VideoCard.vue';
import {VideoApi} from '../api/video';
import {SearchResults, SearchCombination} from '../types/video';

export default defineComponent({
  name: 'SearchPage',
  components: {
    Search,
    Filter,
    Back,
    Loading,
    Close,
    RefreshRight,
    VideoCard
  },
  setup() {
    const router = useRouter();
    const route = useRoute();

    // 基础搜索状态
    const searchQuery = ref('');
    const isLoading = ref(false);
    const loadingMore = ref(false);
    const showAdvancedSearch = ref(false);

    // 搜索结果和选项
    const searchResults = ref<SearchResults>({
      total_pages: 0,
      page: 1,
      has_next: false,
      basic_videos: [],
      detailed_videos: []
    });

    const searchCombination = ref<SearchCombination>({
      video_types: [],
      tags: {},
      sort: []
    });

    // 分页和无限加载
    const currentPage = ref(1);
    const hasMore = computed(() => searchResults.value.has_next);
    const loadMoreTrigger = ref<HTMLElement | null>(null);
    const observer = ref<IntersectionObserver | null>(null);

    // 高级搜索过滤器
    const selectedGenre = ref('');
    const selectedTags = ref<Record<string, boolean>>({});
    const selectedSort = ref('');
    const broadSearch = ref(false);

    // 日期选择相关
    const currentYear = new Date().getFullYear();
    const availableYears = ref<number[]>([]);
    const selectedYear = ref<number | null>(null);
    const selectedMonth = ref<number | null>(null);

    // 生成可选年份列表（从1990年到当前年份）
    for (let year = currentYear; year >= 1990; year--) {
      availableYears.value.push(year);
    }

    const videoQuality = reactive({
      uncensored: false,
      aiUncensored: false,
      chineseSubtitle: false,
      hd: false,
      fps60: false
    });

    // 计算属性
    const hasResults = computed(() => {
      return searchResults.value &&
          (searchResults.value.basic_videos.length > 0 ||
              searchResults.value.detailed_videos.length > 0 ||
              (isLoading.value && searchQuery.value));
    });

    const showNoResults = computed(() => {
      return !isLoading.value &&
          searchResults.value &&
          searchResults.value.basic_videos.length === 0 &&
          searchResults.value.detailed_videos.length === 0 &&
          (searchQuery.value || hasActiveFilters.value);
    });

    const hasActiveFilters = computed(() => {
      return selectedGenre.value ||
          getSelectedTagsArray().length > 0 ||
          selectedSort.value ||
          selectedYear.value !== null ||
          selectedMonth.value !== null ||
          Object.values(videoQuality).some(v => v);
    });

    // 获取选中的标签数组
    const getSelectedTagsArray = () => {
      return Object.entries(selectedTags.value)
          .filter(([_, selected]) => selected)
          .map(([tag]) => tag);
    };

    // 从URL参数初始化搜索状态
    const initFromUrlParams = () => {
      const query = route.query.query as string;
      const page = parseInt(route.query.page as string) || 1;
      const genre = route.query.genre as string;
      const sort = route.query.sort as string;
      const broad = route.query.broad === 'true';
      const tags = route.query.tags as string[] || [];
      const year = parseInt(route.query.year as string) || null;
      const month = parseInt(route.query.month as string) || null;

      searchQuery.value = query || '';
      currentPage.value = page;
      selectedGenre.value = genre || '';
      selectedSort.value = sort || '';
      broadSearch.value = broad;
      selectedYear.value = year;
      selectedMonth.value = month;

      // 重置标签选择
      selectedTags.value = {};

      // 设置选中的标签
      if (Array.isArray(tags)) {
        tags.forEach(tag => {
          selectedTags.value[tag] = true;
        });
      } else if (tags) {
        selectedTags.value[tags] = true;
      }

      // 如果有查询参数，执行搜索
      if (query || genre || tags.length || sort || year || month) {
        handleSearch(false);
      } else {
        // 没有查询参数，执行初始化搜索
        loadInitialResults();
      }
    };

    // 添加初始化加载方法
    const loadInitialResults = async () => {
      isLoading.value = true;

      try {
        const response = await VideoApi.searchVideos({});
        searchResults.value = response;
      } catch (error) {
        console.error('加载初始数据失败:', error);
      } finally {
        isLoading.value = false;
      }
    };

    // 获取搜索组合选项
    const fetchSearchCombination = async () => {
      try {
        const response = await VideoApi.getSearchCombination();
        searchCombination.value = response;
      } catch (error) {
        console.error('获取搜索选项失败:', error);
      }
    };

    // 执行搜索
    const handleSearch = async (updateUrl = true) => {
      // 重置页码
      currentPage.value = 1;
      searchResults.value = {
        total_pages: 0,
        page: 1,
        has_next: false,
        basic_videos: [],
        detailed_videos: []
      };

      isLoading.value = true;

      try {
        // 更新URL参数
        if (updateUrl) {
          updateUrlParams();
        }

        const params = buildSearchParams();
        const response = await VideoApi.searchVideos(params);

        searchResults.value = response;
      } catch (error) {
        console.error('搜索失败:', error);
        ElMessage.error('搜索失败，请稍后重试');
      } finally {
        isLoading.value = false;
      }
    };

    // 加载更多结果
    const loadMore = async () => {
      if (!hasMore.value || loadingMore.value) return;

      loadingMore.value = true;

      try {
        currentPage.value++;
        const params = buildSearchParams();
        const response = await VideoApi.searchVideos(params);

        // 合并结果
        if (response.basic_videos.length) {
          searchResults.value.basic_videos = [
            ...searchResults.value.basic_videos,
            ...response.basic_videos
          ];
        }

        if (response.detailed_videos.length) {
          searchResults.value.detailed_videos = [
            ...searchResults.value.detailed_videos,
            ...response.detailed_videos
          ];
        }

        searchResults.value.has_next = response.has_next;
        searchResults.value.total_pages = response.total_pages;
      } catch (error) {
        console.error('加载更多失败:', error);
      } finally {
        loadingMore.value = false;
      }
    };

    // 构建搜索参数
    const buildSearchParams = () => {
      const params: any = {
        page: currentPage.value
      };

      if (searchQuery.value) params.query = searchQuery.value;
      if (selectedGenre.value) params.genre = selectedGenre.value;
      if (selectedSort.value) params.sort = selectedSort.value;

      // 标签参数，使用数组格式
      const tags = getSelectedTagsArray();
      if (tags.length) params.tags = tags;

      // 广泛搜索
      if (broadSearch.value) params.broad = true;

      // 添加日期参数
      if (selectedYear.value) params.year = selectedYear.value;
      if (selectedMonth.value) params.month = selectedMonth.value;


      return params;
    };

    // 更新URL参数
    const updateUrlParams = () => {
      const query: Record<string, any> = {};

      if (searchQuery.value) query.query = searchQuery.value;
      if (selectedGenre.value) query.genre = selectedGenre.value;
      if (selectedSort.value) query.sort = selectedSort.value;
      if (broadSearch.value) query.broad = broadSearch.value;

      // 标签参数，使用数组格式
      const tags = getSelectedTagsArray();
      if (tags.length) query.tags = tags;

      // 添加日期参数到 URL
      if (selectedYear.value) query.year = selectedYear.value;
      if (selectedMonth.value) query.month = selectedMonth.value;


      router.push({query});
    };

    // 切换视频类型过滤
    const toggleGenre = (genre: string) => {
      selectedGenre.value = selectedGenre.value === genre ? '' : genre;
    };

    // 切换标签选择
    const toggleTag = (tag: string) => {
      selectedTags.value[tag] = !selectedTags.value[tag];
    };

    // 清除日期过滤器
    const clearDateFilter = () => {
      selectedYear.value = null;
      selectedMonth.value = null;
    };


    // 应用高级搜索
    const applyAdvancedSearch = () => {
      showAdvancedSearch.value = false;
      handleSearch();
    };

    // 清除所有过滤器
    const resetFilters = () => {
      selectedGenre.value = '';
      selectedTags.value = {};
      selectedSort.value = '';
      broadSearch.value = false;
      selectedYear.value = null;
      selectedMonth.value = null;
      videoQuality.uncensored = false;
      videoQuality.aiUncensored = false;
      videoQuality.chineseSubtitle = false;
      videoQuality.hd = false;
      videoQuality.fps60 = false;
    };

    // 清除类型过滤
    const clearGenre = () => {
      selectedGenre.value = '';
      handleSearch();
    };

    // 移除标签
    const removeTag = (tag: string) => {
      selectedTags.value[tag] = false;
      handleSearch();
    };

    // 设置排序方式
    const setSortBy = (sortBy: string) => {
      selectedSort.value = selectedSort.value === sortBy ? '' : sortBy;
    };

    // 跳转到视频详情页
    const goToVideo = (videoId: string) => {
      router.push(`/video/${videoId}`);
    };

    // 设置无限加载
    const setupInfiniteLoading = () => {
      if (observer.value) {
        observer.value.disconnect();
      }

      nextTick(() => {
        if (loadMoreTrigger.value) {
          observer.value = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore.value && !loadingMore.value) {
              loadMore();
            }
          }, {threshold: 0.5});

          observer.value.observe(loadMoreTrigger.value);
        }
      });
    };

    // 监听路由变化
    watch(() => route.query, () => {
      initFromUrlParams();
    });

    // 监听搜索结果变化，更新无限加载
    watch(() => searchResults.value, () => {
      setupInfiniteLoading();
    }, {deep: true});

    // 添加生命周期钩子，处理标签导航的初始化和滑动
    onMounted(() => {
      fetchSearchCombination();
      initFromUrlParams();
      setupInfiniteLoading();
      
      // 确保标签栏初始定位正确
      nextTick(() => {
        adjustTabsNavPosition();
      });
    });

    // 调整标签导航条位置的方法
    const adjustTabsNavPosition = () => {
      setTimeout(() => {
        const tabsNavWrap = document.querySelector('.tag-tabs .el-tabs__nav-wrap') as HTMLElement;
        const tabsNav = document.querySelector('.tag-tabs .el-tabs__nav') as HTMLElement;
        
        if (tabsNavWrap && tabsNav) {
          // 移除可能的内联样式
          tabsNav.style.transform = '';
          tabsNavWrap.scrollLeft = 0;
        }
      }, 50);
    };

    // 监听高级搜索对话框的打开，确保标签正确渲染
    watch(() => showAdvancedSearch, (newVal) => {
      if (newVal) {
        nextTick(() => {
          adjustTabsNavPosition();
        });
      }
    });

    onUnmounted(() => {
      if (observer.value) {
        observer.value.disconnect();
      }
    });

    return {
      searchQuery,
      isLoading,
      loadingMore,
      searchResults,
      searchCombination,
      currentPage,
      hasMore,
      loadMoreTrigger,
      selectedGenre,
      selectedTags,
      selectedSort,
      broadSearch,
      selectedYear,
      selectedMonth,
      availableYears,
      videoQuality,
      showAdvancedSearch,
      hasResults,
      showNoResults,
      hasActiveFilters,
      handleSearch,
      toggleGenre,
      toggleTag,
      applyAdvancedSearch,
      resetFilters,
      clearGenre,
      removeTag,
      setSortBy,
      goToVideo,
      getSelectedTagsArray,
      clearDateFilter
    };
  }
});
</script>

<style scoped>
.search-header {
  background: var(--bg-secondary-color);
  padding: 24px 0 18px 0;
  border-radius: 12px;
  margin-bottom: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  justify-content: center;
}

.search-container {
  display: flex;
  gap: 10px;
  width: 100%;
  max-width: 520px;
  align-items: center;
}

.search-input {
  flex: 1;
  font-size: 18px !important;
  height: 44px !important;
  border-radius: 8px !important;
}

.search-button,
.filter-button {
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
}

/* 活跃过滤器标签样式 */
.active-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 15px 0;
  padding: 10px 15px;
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.filter-tag {
  margin-right: 0;
}

/* 高级搜索对话框样式 */
:deep(.advanced-search-dialog) {
  border-radius: 12px;
  overflow: hidden;
  max-width: 95vw;
}

:deep(.advanced-search-dialog .el-dialog__header) {
  background-color: var(--bg-color);
  color: var(--text-color);
  padding: 15px 20px;
  margin: 0;
  border-bottom: 1px solid var(--border-color, #3f3f46);
}

:deep(.advanced-search-dialog .el-dialog__body) {
  background-color: var(--bg-color);
  color: var(--text-color);
  padding: 20px;
}

:deep(.advanced-search-dialog .el-dialog__footer) {
  background-color: var(--bg-color);
  border-top: 1px solid var(--border-color, #3f3f46);
  padding: 15px 20px;
}

.advanced-search-container {
  max-width: 900px;
  margin: 0 auto;
}

.filter-section {
  margin-bottom: 30px;
}

.section-title {
  font-size: 18px;
  margin-bottom: 15px;
  color: var(--text-secondary-color);
  padding-left: 12px;
  position: relative;
}

.section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #ec4899; /* 粉色 */
  border-radius: 2px;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* 类型和排序方式标签样式 */
.filter-option-tag {
  cursor: pointer;
  transition: all 0.2s;
  background-color: var(--bg-secondary-color, #3f3f46) !important;
  border-color: var(--border-color, #52525b) !important;
  color: var(--text-color, #d4d4d8) !important;
  padding: 8px 15px !important;
  font-size: 14px !important;
  border-radius: 20px !important;
}

.filter-option-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  background-color: var(--bg-hover-color, #4b5563) !important;
}

.filter-option-tag.active {
  background-color: #ec4899 !important;
  border-color: #ec4899 !important;
  color: white !important;
}

/* 标签切换和广泛匹配开关样式优化 */
.tag-filter-header {
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.match-switch {
  align-self: flex-start;
}

.match-tip {
  font-size: 12px;
  color: var(--text-secondary-color);
  line-height: 1.4;
}

.tag-tabs {
  margin-top: 15px;
}

/* 支持标签栏滑动，修复间隙问题 */
:deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
  position: relative;
  padding: 0;
  margin: 0;
  scroll-behavior: smooth;
}

:deep(.el-tabs__nav-scroll) {
  overflow: visible;
  display: flex;
  padding: 0;
  margin: 0;
}

:deep(.el-tabs__nav) {
  white-space: nowrap;
  padding: 0 0 4px 0; /* 防止滚动条遮挡内容 */
  position: relative;
  transform: none !important; /* 防止元素库自动添加transform导致定位问题 */
  float: none;
  margin: 0;
}

:deep(.el-tabs__active-bar) {
  position: absolute;
  bottom: 0;
}

/* 修复左边距问题 */
:deep(.el-tabs__header) {
  padding: 0;
  margin: 0 0 15px 0;
}

:deep(.el-tabs__nav-wrap::before) {
  display: none; /* 移除可能的伪元素 */
}

/* 修复左右箭头导致的间隙问题 */
:deep(.el-tabs__nav-prev),
:deep(.el-tabs__nav-next) {
  opacity: 0;
  pointer-events: none;
  width: 0;
  padding: 0;
  margin: 0;
}

/* 让内容可以完整滑动 */
:deep(.tag-tabs .el-tabs__content) {
  width: 100%;
  overflow-x: hidden;
}

/* 确保完整的滑动控制 */
:deep(.el-tabs__nav-wrap::after) {
  height: 1px; /* 减小下划线高度 */
  bottom: 0;
}

/* 隐藏滚动条但保留功能 */
:deep(.el-tabs__nav-wrap::-webkit-scrollbar) {
  height: 2px;
  background-color: transparent;
}

:deep(.el-tabs__nav-wrap::-webkit-scrollbar-thumb) {
  background-color: rgba(145, 145, 145, 0.3);
  border-radius: 2px;
}

/* 标签页样式调整 */
:deep(.el-tabs__item) {
  padding: 0 16px;
  height: 38px;
  line-height: 38px;
  font-size: 14px;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0; /* 防止标签被压缩 */
}

:deep(.el-tabs__item:first-child) {
  padding-left: 0; /* 第一个标签去除左内边距 */
}

/* 确保卡片式标签没有边距 */
:deep(.el-tabs--card > .el-tabs__header) {
  margin: 0 0 15px 0;
  border: none;
}

:deep(.el-tabs--card > .el-tabs__header .el-tabs__nav) {
  border: none;
}

/* 优化高级搜索弹窗在手机端的适配 */
@media (max-width: 768px) {
  .tag-filter-header {
    gap: 5px;
  }
  
  .match-tip {
    font-size: 11px;
  }

  :deep(.el-tabs__item) {
    padding: 0 12px;
    font-size: 13px;
    height: 34px;
    line-height: 34px;
  }
  
  :deep(.tag-tabs .el-tabs__header) {
    margin: 0 0 10px 0;
  }
  
  .tag-options {
    padding-bottom: 8px; /* 为手机端提供更多底部间距 */
  }
}

@media (max-width: 480px) {
  :deep(.el-tabs__item) {
    padding: 0 10px;
    font-size: 12px;
    height: 30px;
    line-height: 30px;
  }
  
  .match-tip {
    font-size: 10px;
  }
}

/* 日期选择器样式 */
.date-selector {
  width: 100%;
}

.year-month-selector {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.year-selector,
.month-selector {
  flex: 1;
}

.year-select,
.month-select {
  width: 100%;
}

.date-actions {
  display: flex;
  justify-content: flex-start;
  margin-top: 15px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
}

/* 搜索结果容器 */
.search-results-container {
  margin-top: 20px;
}

.results-title {
  font-size: 20px;
  margin-bottom: 20px;
  color: var(--text-color);
  border-left: 4px solid var(--primary-color);
  padding-left: 10px;
}

.result-section-title {
  font-size: 18px;
  margin: 25px 0 15px;
  color: var(--text-color);
  border-left: 3px solid var(--secondary-color);
  padding-left: 10px;
}

/* 长图视频网格布局 (基础视频) */
.video-grid-basic {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

/* 宽图视频网格布局 (详细视频) */
.video-grid-detailed {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-header {
    padding: 16px 0 12px 0;
    margin-bottom: 12px;
  }
  .search-container {
    max-width: 100%;
    gap: 6px;
  }
  .search-input {
    font-size: 16px !important;
    height: 38px !important;
  }
  .search-button, .filter-button {
    height: 38px;
    font-size: 14px;
  }
  .video-grid-basic {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  
  .video-grid-detailed {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .results-title {
    font-size: 18px;
    margin-bottom: 15px;
  }
  
  .result-section-title {
    font-size: 16px;
    margin: 20px 0 12px;
  }
}

@media (max-width: 480px) {
  .search-header {
    padding: 10px 0 8px 0;
    margin-bottom: 8px;
  }
  .search-container {
    gap: 4px;
  }
  .search-input {
    font-size: 15px !important;
    height: 32px !important;
  }
  .search-button, .filter-button {
    height: 32px;
    font-size: 13px;
  }
  .video-grid-basic {
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  
  .video-grid-detailed {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  
  .results-title {
    font-size: 16px;
    margin-bottom: 12px;
  }
  
  .result-section-title {
    font-size: 15px;
    margin: 15px 0 10px;
  }
}

.tag-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
}

/* 标签样式，与VideoDetailPage保持一致 */
.tag-item {
  cursor: pointer;
  transition: all 0.2s;
  background-color: var(--bg-secondary-color, #3f3f46) !important;
  border-color: var(--border-color, #52525b) !important;
  color: var(--text-color, #d4d4d8) !important;
  padding: 8px 15px !important;
  font-size: 14px !important;
}

.tag-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  background-color: var(--bg-hover-color, #4b5563) !important;
}

.tag-item.active {
  background-color: #ec4899 !important;
  border-color: #ec4899 !important;
  color: white !important;
}

/* 优化高级搜索弹窗在手机端的适配 */
:deep(.advanced-search-dialog) {
  border-radius: 12px;
  overflow: hidden;
  max-width: 95vw;
}

@media (max-width: 768px) {
  :deep(.advanced-search-dialog) {
    width: 98vw !important;
    min-width: 0 !important;
    max-width: 98vw !important;
  }
  
  :deep(.advanced-search-dialog .el-dialog__body) {
    padding: 10px !important;
  }
  
  .advanced-search-container {
    padding: 0 2px;
  }
  
  .filter-options, .tag-options {
    gap: 6px;
  }
  
  .filter-option-tag, .tag-item {
    font-size: 12px !important;
    padding: 6px 10px !important;
  }
}

@media (max-width: 480px) {
  :deep(.advanced-search-dialog) {
    width: 100vw !important;
    min-width: 0 !important;
    max-width: 100vw !important;
    border-radius: 0 !important;
  }
  
  :deep(.advanced-search-dialog .el-dialog__body) {
    padding: 4px !important;
  }
  
  .advanced-search-container {
    padding: 0 1px;
  }
  
  .filter-options, .tag-options {
    gap: 3px;
  }
  
  .filter-option-tag, .tag-item {
    font-size: 11px !important;
    padding: 4px 7px !important;
  }
}
</style> 
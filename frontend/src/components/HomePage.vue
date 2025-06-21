<template>
  <div class="page-container">
    <!-- Banner区域 -->
    <banner-slider :banner="homeData.banners"/>

    <!-- 视频区块通用组件 -->
    <template v-for="(section, index) in homeData.latest_videos" :key="`latest-${index}`">
      <video-section
        :title="section.title"
        :search-suffix="section.search_suffix"
        :videos="section.videos"
        item-class="latest-horizontal-item"
        thumbnail-class="portrait"
        @view-more="handleViewMore"
        @video-click="handleVideoClick"
      />
    </template>

    <!-- 其他视频分类 -->
    <template v-for="(section, key) in filteredVideoSections" :key="key">
      <video-section 
        v-if="section[0]?.videos?.length"
        :title="section[0].title" 
        :search-suffix="section[0].search_suffix" 
        :videos="section[0].videos"
        thumbnail-class="landscape" 
        @view-more="handleViewMore"
        @video-click="handleVideoClick"
      />
    </template>

    <!-- 返回顶部按钮 -->
    <el-backtop :right="20" :bottom="20"></el-backtop>
  </div>
</template>

<script lang="ts">
import {computed, defineComponent, onMounted, ref} from 'vue';
import {useRouter} from 'vue-router';
import {VideoApi} from '../api/video';
import {HomeData} from '../types/video';
import BannerSlider from '../components/BannerSlider.vue';
import VideoSection from '../components/VideoSection.vue';

export default defineComponent({
  name: 'HomePage',
  components: {
    BannerSlider,
    VideoSection
  },
  setup() {
    const router = useRouter();
    const homeData = ref<HomeData>({
      banners: {
        video_id: '',
        title: '',
        cover_url: ''
      },
      latest_videos: [],
      new_arrivals_videos: [],
      new_uploads_videos: [],
      chinese_subtitle_videos: [],
      daily_rank_videos: [],
      monthly_rank_videos: [],
    });

    const filteredVideoSections = computed(() => ({
      new_arrivals: homeData.value.new_arrivals_videos,
      new_uploads: homeData.value.new_uploads_videos,
      chinese_subtitle: homeData.value.chinese_subtitle_videos,
      daily_rank: homeData.value.daily_rank_videos,
      monthly_rank: homeData.value.monthly_rank_videos
    }));

    const fetchHomeData = async () => {
      homeData.value = await VideoApi.getHomeData();
    };

    const handleVideoClick = (videoId: string) => {
      router.push(`/video/${videoId}`);
    };

    const handleViewMore = (searchSuffix: string) => {
      if (searchSuffix) {
        router.push(`/search?${searchSuffix}`);
      }
    };

    onMounted(fetchHomeData);

    return {
      homeData,
      filteredVideoSections,
      fetchHomeData,
      handleVideoClick,
      handleViewMore,
    };
  },
});
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px;
  background-color: #18181b;
  min-height: 100vh;
  color: #fff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-container {
    padding: 8px;
  }
}

@media (max-width: 480px) {
  .page-container {
    padding: 5px;
  }
}
</style> 
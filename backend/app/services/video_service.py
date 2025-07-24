from DrissionPage.common import make_session_ele

from app.models.video import *
from app.config import settings, logger
from app.utils.cloudflare_bypass import CloudflareBypasser
from app.utils.chinese_converter import to_simplified, convert_dict, convert_list

import re
import json


class VideoService:
    def __init__(self):
        """初始化视频服务"""
        self.cf_bypasser = CloudflareBypasser()

    async def get_home_data(self) -> HomeData:
        """获取首页数据，包括头图和推荐视频"""
        try:
            page_content = await self.cf_bypasser.get_request(settings.HANIME_BASE_URL)
            if not page_content:
                return HomeData(error="Failed to fetch page content.")

            page_ele = make_session_ele(page_content)

            # 获取头图数据
            banner_data = self._extract_banner_data(page_ele)

            # 获取推荐视频数据
            recommended_elem = page_ele.ele('xpath://div[@id="home-rows-wrapper"]')
            if not recommended_elem:
                return HomeData(
                    banners=banner_data,
                    error="无法获取推荐视频数据"
                )

            # 单独处理最新视频（结构不同）
            latest_videos = self._extract_latest_videos(recommended_elem)

            # 处理其他视频分类（结构相同）
            other_video_sections = [
                {"name": "new_arrivals_videos", "display_name": "最新上市", "index": "2"},
                {"name": "new_uploads_videos", "display_name": "最新上传", "index": "3"},
                {"name": "chinese_subtitle_videos", "display_name": "中文字幕", "index": "4"},
                {"name": "daily_rank_videos", "display_name": "本日排行", "index": "last()-2"},
                {"name": "monthly_rank_videos", "display_name": "本月排行", "index": "last()-1"}
            ]

            # 创建HomeData对象
            home_data = HomeData(
                banners=banner_data,
                latest_videos=latest_videos
            )

            # 处理其他视频分类
            for section in other_video_sections:
                section_name = section["name"]
                display_name = section["display_name"]
                index = section["index"]

                section_data = self._extract_section_videos(recommended_elem, index, display_name)
                setattr(home_data, section_name, section_data)

            return home_data
        except Exception as e:
            logger.exception(f"首页数据获取错误: {str(e)}")
            return HomeData(error=str(e))

    def _extract_banner_data(self, page_ele) -> BannerVideo:
        """提取首页头图数据"""
        banner_img_ele = page_ele.ele("xpath://div[@class='hidden-xs']//img[2]")
        banner_title_ele = page_ele.ele("xpath://div[@id='home-banner-wrapper']//h1")
        banner_desc_ele = page_ele.ele("xpath://div[@id='home-banner-wrapper']//h4")

        image_url = banner_img_ele.attr("src") if banner_img_ele else ""
        video_id = self._extract_video_id_from_image(image_url)

        return BannerVideo(
            video_id=video_id,
            cover_url=image_url,
            title=banner_title_ele.text.strip() if banner_title_ele else "",
            description=banner_desc_ele.text.strip() if banner_desc_ele else ""
        )

    def _extract_latest_videos(self, recommended_elem) -> List[Dict[str, Any]]:
        """提取最新视频（特殊结构）"""
        latest_videos = []

        latest_videos_ele = recommended_elem.ele("xpath:./a[1]")
        if not latest_videos_ele:
            return []

        search_url = latest_videos_ele.attr("href") if latest_videos_ele else ""
        search_suffix = search_url.split("?")[1] if search_url and "?" in search_url else ""

        # 获取相邻的视频容器div
        latest_videos_div = latest_videos_ele.ele("xpath:./following-sibling::div")
        if not latest_videos_div:
            return []

        # 获取所有 a 标签（注意与其他分类不同）
        video_info_ele = latest_videos_div.eles("xpath:.//a")
        video_info = []

        # 用于跟踪已处理的视频ID，避免重复
        seen_video_ids = set()

        for video_ele in video_info_ele:
            video_url = video_ele.attr("href")
            video_id = self._extract_video_id_from_url(video_url)

            # 跳过已处理的视频ID
            if video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)

            # 获取 img
            img_ele = video_ele.ele("xpath:.//img")
            img_url = img_ele.attr("src") if img_ele else ""

            # 获取视频名
            title_ele = video_ele.ele("xpath:.//div[1]")
            title = title_ele.text.strip() if title_ele else ""

            video_info.append(
                VideoBase(
                    video_id=video_id,
                    cover_url=img_url,
                    title=title
                )

            )

        latest_videos.append({
            "title": "最新视频",
            "search_suffix": to_simplified(search_suffix),
            "videos": video_info
        })

        return latest_videos

    def _extract_section_videos(self, recommended_elem, index, display_name) -> List[Dict[str, Any]]:
        """提取特定分区的视频列表"""
        section_videos = []

        # 获取分区标题元素
        section_ele = recommended_elem.ele(f"xpath:./a[position()={index}]")
        if not section_ele:
            return []

        search_url = section_ele.attr("href") if section_ele else ""
        search_suffix = search_url.split("?")[1] if search_url and "?" in search_url else ""

        # 获取相邻的视频容器div
        videos_div = section_ele.ele("xpath:./following-sibling::div")
        if not videos_div:
            return []

        # 获取所有含有title属性的div
        video_elements = videos_div.eles("xpath:.//div[@title]")
        video_info_list = []

        # for video_ele in video_elements:
        #     video_info = self._extract_video_info(video_ele)
        #     video_info_list.append(video_info)

        # 每隔一个取一个（取第1、3、5...个）
        for i in range(0, len(video_elements), 2):
            video_ele = video_elements[i]
            video_info = self._extract_detailed_video_info(video_ele)
            if video_info:
                video_info_list.append(video_info)

        section_videos.append({
            "title": display_name,
            "search_suffix": to_simplified(search_suffix),
            "videos": video_info_list
        })

        return section_videos

    def _extract_detailed_video_info(self, video_ele) -> Optional[VideoPreview]:
        """从单个 详细视频 元素中提取信息"""
        try:
            # 获取视频标题
            title_elem = video_ele.s_ele("xpath:.//*[contains(@class, 'card-mobile-title')]")
            video_title = (title_elem.text.strip() if title_elem else None) or ""

            # 获取视频链接
            overlay_ele = video_ele.ele("xpath:.//a[@class='overlay']")
            video_url = overlay_ele.attr("href") if overlay_ele else ""

            video_id = self._extract_video_id_from_url(video_url)

            # 如果没有视频ID则跳过
            if not video_id:
                return None

            # 获取封面图
            img_ele = video_ele.ele("xpath:.//img[contains(@style, 'object-fit: cover')]")
            img_url = img_ele.attr("src") if img_ele else ""

            # 获取时长
            duration_ele = video_ele.ele(
                "xpath:.//div[contains(@class, 'card-mobile-duration') and contains(text(), ':')]")
            duration_text = duration_ele.text.strip() if duration_ele else ""

            # 获取点赞率和点赞人数
            like_rate = ""
            like_count = 0
            like_ele = video_ele.ele(
                "xpath:.//div[contains(@class, 'card-mobile-duration') and contains(., 'thumb_up')]")

            if like_ele:
                like_text = like_ele.text.strip()
                # 格式如: 99%&nbsp;(723)
                rate_match = re.search(r'(\d+)%', like_text)
                if rate_match:
                    like_rate = rate_match.group(1) + "%"

                count_match = re.search(r'\((\d+)\)', like_text)
                if count_match:
                    like_count = int(count_match.group(1))

            # 获取观看次数
            views_text = ""
            views_ele = video_ele.ele(
                "xpath:.//div[contains(@class, 'card-mobile-duration') and contains(text(), '次')]")
            if views_ele:
                views_text = views_ele.text.strip()

            # 获取发行商信息
            studio = {}
            studio_ele = video_ele.ele("xpath:.//a[contains(@class, 'card-mobile-user')]")
            if studio_ele:
                studio_name = studio_ele.text.strip()
                studio_url = studio_ele.attr("href") if studio_ele else ""
                # 从URL中提取查询参数
                studio_query = studio_url.split("?")[1] if studio_url and "?" in studio_url else ""

                studio = VideoStudio(
                    name=studio_name,
                    query=studio_query
                )

            return VideoPreview(
                video_id=video_id,
                cover_url=img_url,
                title=video_title,
                duration=duration_text,
                view_count=self._parse_views(views_text),
                like_rate=like_rate,
                like_count=like_count,
                studio=studio
            )

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            logger.error(f"提取视频信息错误: {str(e)}")
            return None

    def _extract_based_video_info(self, item) -> Optional[VideoBase]:
        """从单个 基础视频 元素中提取信息"""
        try:
            parent_link = item.s_ele("xpath:./parent::a")
            href = (parent_link.attr("href") if parent_link else None) or ""
            rel_video_id = self._extract_video_id(href)
            # 跳过非视频链接
            if not rel_video_id:
                return None

            title_elem = item.s_ele("xpath:.//div[contains(@class, 'home-rows-videos-title')]")
            rel_title = (title_elem.text.strip() if title_elem else None) or ""

            img_elem = item.s_ele("xpath:.//img")
            rel_cover_url = (img_elem.attr("src") if img_elem else None) or ""

            return VideoBase(
                video_id=rel_video_id,
                title=rel_title,
                cover_url=rel_cover_url,
            )

        except Exception as e:
            logger.exception(f"解析相关视频项错误: {str(e)}")
            return None

    # 转换 观看次数
    def _parse_views(self, views_text: str) -> int:
        """解析观看次数文本"""
        if not views_text: return 0
        # Handle "萬" and "千"
        num_part = views_text
        multiplier = 1
        if "萬" in views_text:
            num_part = views_text.split("萬")[0]
            multiplier = 10000
        elif "千" in views_text:  # Assuming "千" for thousands
            num_part = views_text.split("千")[0]
            multiplier = 1000

        try:
            # Remove non-numeric parts except decimal for parsing float first
            num_str = re.sub(r'[^\d.]', '', num_part)
            if not num_str: return 0
            return int(float(num_str) * multiplier)
        except ValueError:
            # Fallback for simple integer parsing if float conversion fails or no multiplier
            views_str_digits = re.sub(r'[^\d]', '', views_text)
            try:
                return int(views_str_digits) if views_str_digits else 0
            except ValueError:
                return 0

    async def get_video_detail(self, video_id: str) -> VideoDetail:
        """获取视频详情"""
        try:
            video_url = f"{settings.HANIME_BASE_URL}/watch?v={video_id}"
            page_content = await self.cf_bypasser.get_request(video_url)

            # with open('videoDetail.html', 'w', encoding='utf-8') as f:
            #     f.write(page_content)

            page_ele = make_session_ele(page_content)

            # 获取封面和默认视频URL
            video_elem = page_ele.s_ele('xpath://video[@id="player"]')
            cover_url = (video_elem.attr("poster") if video_elem else None) or ""

            # 使用辅助方法提取流媒体URL
            stream_urls_list = self._extract_stream_urls(video_elem)
            default_video_url = stream_urls_list[0].url if stream_urls_list else ""

            # 使用辅助方法提取发行商信息
            video_studio = self._extract_studio_info(page_ele)

            # 获取视频类型
            video_type_ele = page_ele.s_ele('xpath://*[@id="video-artist-name"]/following-sibling::a')
            video_type_name = video_type_ele.text.strip() if video_type_ele else ""
            video_type_url = video_type_ele.attr("href") if video_type_ele else ""
            video_type_query = video_type_url.split("?")[1] if video_type_url and "?" in video_type_url else ""

            video_type = VideoType(
                name=to_simplified(video_type_name),
                query=to_simplified(video_type_query)
            )

            # 获取标题、描述等基本信息
            video_title_ele = page_ele.s_ele("xpath://*[@id='shareBtn-title']")
            video_title = (video_title_ele.text.strip() if video_title_ele else None) or ""

            description_wrapper_elem = page_ele.s_ele(
                'xpath://*[@id="player-div-wrapper"]//div[contains(@class,"video-description-panel")]')

            # 视频观看信息
            video_views_ele = description_wrapper_elem.s_ele('xpath:./div[1]')

            # 正则匹配观看次数和上传日期
            views_match = re.search(r'(\d+(?:\.\d+)?(?:萬|千)?)次\s+(\d{4}-\d{2}-\d{2})', video_views_ele.text.strip())
            views_str = ""
            upload_date_str = ""

            if views_match:
                views_str = views_match.group(1)
                upload_date_str = views_match.group(2)

            # 副标题
            subtitle_ele = description_wrapper_elem.s_ele('xpath:./div[2]')
            subtitle = subtitle_ele.text.strip() if subtitle_ele else ""

            # 描述
            description_ele = description_wrapper_elem.s_ele('xpath:./div[3]')
            description = description_ele.text.strip() if description_ele else ""

            # 使用辅助方法提取标签
            tags = self._extract_tags(page_ele)

            # 使用辅助方法提取系列视频
            series_videos = self._extract_series_videos(page_ele)

            # 使用辅助方法提取相关视频（两种类型）
            basic_related_videos = self._extract_related_videos_based(page_ele)
            detailed_related_videos = self._extract_related_videos_detailed(page_ele)

            # 创建VideoDetail对象
            video_detail = VideoDetail(
                video_id=video_id,
                title=video_title,
                subtitle=to_simplified(subtitle),
                cover_url=cover_url,
                description=to_simplified(description),
                default_video_url=default_video_url,
                stream_urls=stream_urls_list,
                view_count=self._parse_views(views_str),
                upload_date=upload_date_str,
                studio=video_studio,
                video_type=video_type,
                tags=tags,
                series_videos=series_videos,
                basic_related_videos=basic_related_videos,
                detailed_related_videos=detailed_related_videos
            )

            return video_detail

        except Exception as e:
            # import traceback
            # traceback.print_exc()
            logger.error(f"获取视频详情错误: {str(e)}")

            return VideoDetail(video_id=video_id, title="")

    # 获取视频评论
    async def get_video_comments(self, video_id: str) -> List[VideoComment]:
        """获取视频播放评论"""
        try:
            video_load_comment_url = f"{settings.HANIME_BASE_URL}/loadComment"
            params = {
                "id": video_id,
                "type": "video",
                "content": "comment-tablink"
            }
            respond = await self.cf_bypasser.get_request(video_load_comment_url, params=params)
            page_content = json.loads(respond).get("comments", "")

            # 在外层包一层 html
            page_content = f"<html>{page_content}</html>"
            page_ele = make_session_ele(page_content)

            if page_ele is None:
                logger.error("解析评论错误: 无法获取评论元素")
                return []

            # 获取视频评论
            video_comments = []
            # 获取所有的评论元素
            comment_elements = page_ele.eles('xpath://*[@id="comment-like-form-wrapper"]')

            for comment_elem in comment_elements:
                try:
                    # 获取评论ID（如果没有评论回复，则没有评论ID）
                    comment_id = ""
                    # 找到 包含 data-commentid 属性的div
                    load_replies_btn = comment_elem.ele("xpath:.//div[@data-commentid]")
                    if load_replies_btn:
                        comment_id = load_replies_btn.attr("data-commentid")

                    # 获取用户头像
                    user_avatar_ele = comment_elem.ele("xpath:./preceding-sibling::a[1]//img")
                    user_avatar = user_avatar_ele.attr("src") if user_avatar_ele else ""

                    # 获取用户名和评论时间
                    username_ele = comment_elem.ele("xpath:./preceding-sibling::div[1]//div[contains(@class, 'comment-index-text')][1]//a")
                    username_time_text = username_ele.text if username_ele else ""

                    # 分割用户名和时间
                    username = ""
                    comment_time = ""
                    if username_time_text:
                        # 使用正则表达式分离用户名和时间
                        match = re.match(r'(.+?)(?:\s+(\d+.+))?$', username_time_text)
                        if match:
                            username = match.group(1).strip()
                            # 如果从正则获取，使用它；否则从span标签获取
                            comment_time = match.group(2).strip() if match.group(2) else ""

                    # 如果上面的方法没提取到时间，尝试从span标签获取
                    if not comment_time:
                        time_ele = username_ele.ele("xpath:.//span")
                        comment_time = time_ele.text.strip() if time_ele else ""

                    # 获取评论内容
                    comment_content_ele = comment_elem.ele("xpath:./preceding-sibling::div[1]//div[contains(@class, 'comment-index-text')][2]")
                    comment_content = comment_content_ele.text.strip() if comment_content_ele else ""

                    # 获取点赞数
                    like_count = 0
                    like_ele = comment_elem.ele("xpath:.//div[contains(., 'thumb_up')]//span[2]")
                    if like_ele:
                        like_text = like_ele.text.strip()
                        try:
                            like_count = int(re.search(r'\d+', like_text).group()) if re.search(r'\d+',
                                                                                                like_text) else 0
                        except:
                            like_count = 0

                    # 获取回复数
                    reply_count = 0
                    reply_btn = comment_elem.ele("xpath:.//div[contains(@class, 'load-replies-btn')]")
                    if reply_btn:
                        reply_text = reply_btn.text.strip()
                        try:
                            # 直接提取数字
                            digits = re.findall(r'\d+', reply_text)
                            reply_count = int(digits[0]) if digits else 0
                        except:
                            reply_count = 0

                    # 使用VideoComment模型
                    comment = VideoComment(
                        comment_id=comment_id,
                        user_avatar=user_avatar,
                        username=username,
                        comment_time=comment_time,
                        comment_content=comment_content,
                        like_count=like_count,
                        reply_count=reply_count
                    )
                    video_comments.append(comment)

                except Exception as e:
                    logger.error(f"解析评论错误: {str(e)}")

            return video_comments
        except Exception as e:
            logger.error(f"获取视频评论错误: {str(e)}")
            return []

    # 获取视频评论的相关回复
    async def get_comment_replies(self, comment_id: str) -> List[CommentReply]:
        """获取视频评论的相关回复"""
        try:
            video_load_comment_url = f"{settings.HANIME_BASE_URL}/loadReplies"
            params = {
                "id": comment_id
            }
            respond = await self.cf_bypasser.get_request(video_load_comment_url, params=params)
            page_content = json.loads(respond).get("replies", "")

            # 在外层包一层 html
            page_content = f"<html>{page_content}</html>"
            page_ele = make_session_ele(page_content)

            if page_ele is None:
                logger.error("解析评论回复错误: 无法获取评论元素")
                return []

            # 获取评论回复的根元素
            replies_list = []
            reply_root = page_ele.ele(f'xpath://*[@id="reply-start-{comment_id}"]')

            if not reply_root:
                logger.error(f"未找到评论回复的根元素: reply-start-{comment_id}")
                return []

            # 解析所有回复
            # 使用直接的子元素选择器，不依赖style属性
            # 找到所有回复内容的div，每个回复由两个div组成，第一个包含内容，第二个包含点赞信息
            all_divs = reply_root.eles('xpath:./div')

            # 每两个div构成一个回复（内容div + 点赞div）
            for i in range(0, len(all_divs), 2):
                try:
                    if i + 1 >= len(all_divs):
                        # 确保我们有足够的div来处理一个完整的回复
                        break

                    content_div = all_divs[i]  # 内容div
                    like_div = all_divs[i + 1]  # 点赞div

                    # 获取用户头像
                    user_avatar_ele = content_div.ele("xpath:.//img[contains(@class, 'img-circle')]")
                    user_avatar = user_avatar_ele.attr("src") if user_avatar_ele else ""

                    # 获取用户名和回复时间
                    user_info_div = content_div.ele("xpath:.//div[contains(@class, 'comment-index-text')][1]")
                    user_info_ele = user_info_div.ele("xpath:.//a") if user_info_div else None
                    username_time_text = user_info_ele.text if user_info_ele else ""

                    # 分割用户名和时间
                    username = ""
                    reply_time = ""
                    if username_time_text:
                        # 使用正则表达式分离用户名和时间
                        match = re.match(r'(.+?)(?:\s+(\d+.+))?$', username_time_text)
                        if match:
                            username = match.group(1).strip()
                            reply_time = match.group(2).strip() if match.group(2) else ""

                    # 如果上面的方法没提取到时间，尝试从span标签获取
                    if not reply_time and user_info_ele:
                        time_ele = user_info_ele.ele("xpath:.//span")
                        reply_time = time_ele.text.strip() if time_ele else ""

                    # 获取回复内容
                    content_ele = content_div.ele("xpath:.//div[contains(@class, 'comment-index-text')][2]")
                    reply_content = content_ele.text.strip() if content_ele else ""

                    # 获取点赞数
                    like_count = 0
                    # 第一个div中的第二个span通常包含点赞数
                    like_span = like_div.ele("xpath:.//div[1]//span[2]")
                    if like_span:
                        like_text = like_span.text.strip()
                        # 检查是否有display:none属性
                        display_style = like_span.attr("style")
                        if display_style and "display:none" in display_style:
                            like_count = 0
                        else:
                            try:
                                like_count = int(like_text) if like_text else 0
                            except:
                                # 如果不能直接转换，尝试提取数字
                                digits = re.findall(r'-?\d+', like_text)
                                like_count = int(digits[0]) if digits else 0

                    # 使用CommentReply模型
                    reply = CommentReply(
                        user_avatar=user_avatar,
                        username=username,
                        reply_time=reply_time,
                        reply_content=reply_content,
                        like_count=like_count
                    )
                    replies_list.append(reply)

                except Exception as e:
                    logger.exception("提取评论回复信息错误")
                    continue

            return replies_list

        except Exception as e:
            logger.exception("获取视频评论回复错误")
            return []

    def _extract_video_id(self, url: str) -> str:
        """从URL中提取视频ID"""
        if not url: return ""
        match = re.search(r'[?&]v=([^&]+)', url)
        return match.group(1) if match else ""

    def _extract_video_id_from_image(self, url: str) -> str:
        """从图片URL中提取视频ID"""
        if not url: return ""
        # https://vdownload.hembed.com/image/thumbnail/105277h..1pg?secure=7B0ISpEJXmdy5cRMl0QQKA==,1749868212
        # 提取 105277
        match = re.search(r'/image/thumbnail/(\d+)', url)
        return match.group(1) if match else ""

    def _extract_video_id_from_url(self, video_url: str) -> str:
        """从视频URL中提取视频ID """
        if not video_url: return ""
        # https://hanime1.me/watch?v=109795
        # 提取 109795
        match = re.search(r'/watch\?v=([^&]+)', video_url)
        return match.group(1) if match else ""

    # 辅助方法，提取标签信息
    def _extract_tags(self, page_ele) -> List[VideoTag]:
        """提取视频标签信息"""
        tags = []
        tag_elements = page_ele.eles("xpath://*[contains(@class, 'single-video-tag')]//a[contains(@href, 'tags')]")
        for tag_elem in tag_elements:
            tag_text = (tag_elem.text.strip() if tag_elem else None) or ""
            tag_name = re.sub(r'\s*\(\d+\)$', '', tag_text)

            href = (tag_elem.attr("href") if tag_elem else None) or ""
            tag_search_query = href.split("?")[1] if href and "?" in href else ""
            tag_search_query = tag_search_query.replace("%5B%5D", "")
            if tag_name:  # 确保名称非空
                tags.append(
                    VideoTag(
                        name=to_simplified(tag_name),
                        query=to_simplified(tag_search_query)
                    )
                )
        return tags

    # 辅助方法，提取视频流URL
    def _extract_stream_urls(self, video_elem) -> List[VideoStreamUrl]:
        """提取视频流URL信息"""
        stream_urls_list = []
        # 获取所有的 source 元素
        source_elements = video_elem.eles("xpath:.//source") if video_elem else []
        for source_ele in source_elements:
            # 获取 src 属性
            source_url = source_ele.attr("src")
            if not source_url:
                continue
            # 获取 size 属性 (分辨率)
            size = source_ele.attr("size") + "p" if source_ele.attr("size") else "unknown"

            # 创建 StreamUrl 对象
            stream_urls_list.append(
                VideoStreamUrl(
                    quality=size,
                    url=source_url
                ))
        return stream_urls_list

    # 辅助方法，提取工作室/发行商信息
    def _extract_studio_info(self, page_ele) -> VideoStudio:
        """提取视频发行商信息"""
        studio_img_ele = page_ele.s_ele('xpath://*[@id="video-user-avatar"]/following-sibling::img')
        studio_name_ele = page_ele.s_ele('xpath://*[@id="video-artist-name"]')

        # 发行商信息
        studio_icon_url = studio_img_ele.attr("src") if studio_img_ele else ""
        studio_name = studio_name_ele.text.strip() if studio_name_ele else ""
        studio_url = studio_name_ele.attr("href") if studio_name_ele else ""
        studio_query = studio_url.split("?")[1] if studio_url and "?" in studio_url else ""

        return VideoStudio(
            name=studio_name,
            icon_url=studio_icon_url,
            url=studio_url,
            query=studio_query
        )

    # 辅助方法，提取相关视频信息
    def _extract_related_videos_based(self, page_ele) -> List[VideoBase]:
        """提取相关视频信息"""
        related_videos = []

        # with open('related.html', 'w', encoding='utf-8') as f:
        #     f.write(page_ele.html)

        related_items = page_ele.eles(
            'xpath://*[@id="related-tabcontent"]//*[contains(@class, "home-rows-videos-div")]')

        for item in related_items:
            video_info = self._extract_based_video_info(item)
            if video_info:
                related_videos.append(video_info)

        return related_videos

    def _extract_related_videos_detailed(self, page_ele) -> List[VideoPreview]:
        """提取相关视频信息"""
        related_videos = []
        related_items = page_ele.eles(
            'xpath://*[@id="related-tabcontent"]//div[contains(@class, "related-doujin-videos")]')

        for video_ele in related_items:
            video_info = self._extract_detailed_video_info(video_ele)
            if video_info:
                related_videos.append(video_info)

        return related_videos

    # 辅助方法，提取系列视频信息
    def _extract_series_videos(self, page_ele) -> List[VideoPreview]:
        """提取系列视频信息"""
        series_videos = []
        series_items = page_ele.eles(
            'xpath://*[@id="player-div-wrapper"]//*[@id="playlist-scroll"]//*[contains(@class, "multiple-link-wrapper")]')

        for video_ele in series_items:
            video_info = self._extract_detailed_video_info(video_ele)

            if video_info:
                series_videos.append(video_info)

        return series_videos

    async def get_search_combination(self) -> SearchCombination:
        """获取搜索组合"""
        try:
            search_combination_url = f"{settings.HANIME_BASE_URL}/search"
            page_content = await self.cf_bypasser.get_request(search_combination_url)

            # with open('searchDetail.html', 'w', encoding='utf-8') as f:
            #     f.write(page_content)

            page_ele = make_session_ele(page_content)

            # 获取影片类型
            video_types_eles = page_ele.s_eles("xpath://div[@id='genre-modal']//div[@class='hentai-sort-options']")
            video_types = []
            for video_type_ele in video_types_eles:
                video_type_name = video_type_ele.text.strip()
                video_types.append(video_type_name)

            # 获取标签类型
            tags_dict = {}

            # 找到所有h5和label元素
            all_elements = page_ele.s_eles(
                "xpath://div[@id='tags']//div[@class='modal-body']//*[self::h5 or self::label]")

            current_category = None
            current_tags = []

            # 遍历所有元素，按h5分组
            for element in all_elements:
                tag_name = element.tag

                if tag_name == "h5":
                    # 如果遇到新的h5，保存前一个分类的标签
                    if current_category and current_tags:
                        tags_dict[current_category] = current_tags

                    # 开始新的分类
                    current_category = element.text.strip()
                    current_tags = []
                elif tag_name == "label" and current_category:
                    # 将标签添加到当前分类
                    tag_text = element.text.strip()
                    if tag_text:
                        current_tags.append(tag_text)

            # 添加最后一个分类
            if current_category and current_tags:
                tags_dict[current_category] = current_tags

            # 获取排序方式
            sort_by_eles = page_ele.s_eles("xpath://div[@id='sort-modal']//div[@class='hentai-sort-options']")
            sort_by_options = []
            for sort_by_ele in sort_by_eles:
                sort_by_name = sort_by_ele.text.strip()
                sort_by_options.append(sort_by_name)

            return SearchCombination(
                video_types=convert_list(video_types),
                tags=convert_dict(tags_dict),
                sort=convert_list(sort_by_options)
            )

        except Exception as e:
            logger.exception(f"获取搜索组合错误: {str(e)}")
            return SearchCombination()

    async def search_videos(self,
                            query: Optional[str],
                            genre: Optional[str],
                            tags: Optional[List[str]],
                            broad: Optional[bool],
                            sort: Optional[str],
                            year: Optional[int],
                            month: Optional[int],
                            page: int
                            ) -> SearchResults:
        """搜索视频

        Args:
            query: 搜索关键词
            genre: 视频类型过滤
            tags: 标签过滤
            broad: 宽泛搜索
            sort: 排序方式
            year: 年份
            month: 月份
            page: 页码

        Returns:
            SearchResults: 搜索结果
        """
        try:
            search_url = f"{settings.HANIME_BASE_URL}/search"

            # 构建搜索参数
            params = {}

            # 添加查询关键词
            if query:
                params["query"] = query

            # 添加视频类型
            if genre:
                params["genre"] = genre

            # 添加标签过滤
            if tags and len(tags) > 0:
                for i, tag in enumerate(tags):
                    params[f"tags[{i}]"] = tag

            # 添加排序方式
            if sort:
                params["sort"] = sort

            # 添加页码
            if page > 1:
                params["page"] = str(page)

            if broad:
                params["broad"] = "on"  # 宽泛搜索

            if year:
                params["year"] = year

            if month:
                params["month"] = month

            # 发送请求
            page_content = await self.cf_bypasser.get_request(search_url, params=params)

            # with open('searchDetail.html', 'w', encoding='utf-8') as f:
            #     f.write(page_content)

            if not page_content:
                logger.error("搜索视频失败: 无法获取页面内容")
                return SearchResults()

            page_ele = make_session_ele(page_content)

            # 提取视频总数
            pages_ele = page_ele.s_ele("xpath://ul[@class='pagination']")
            total_pages = 0
            # 检查是否有下一页
            has_next = False

            if pages_ele:
                # 获取倒数第二个li元素
                last_page_li = pages_ele.eles("xpath:.//li")[-2]
                total_pages = int(last_page_li.text.strip()) if last_page_li.text.strip().isdigit() else 0

                if total_pages > page:
                    has_next = True

            detailed_video_list = []
            # 获取所有含有title属性的div
            video_elements = page_ele.eles('xpath://*[@id="home-rows-wrapper"]//div[@title]')

            if video_elements:
                # 每隔一个取一个（取第1、3、5...个）
                for i in range(0, len(video_elements), 2):
                    video_ele = video_elements[i]
                    video_info = self._extract_detailed_video_info(video_ele)
                    if video_info:
                        detailed_video_list.append(video_info)

            basic_video_list = []
            # 提取基本视频信息（可能是另一种布局）
            video_elements = page_ele.eles(
                'xpath://*[@id="home-rows-wrapper"]//*[contains(@class, "home-rows-videos-div")]')

            if video_elements:
                for video_ele in video_elements:
                    video_info = self._extract_based_video_info(video_ele)
                    if video_info:
                        basic_video_list.append(video_info)

            # 创建搜索结果
            return SearchResults(
                total_pages=total_pages,
                page=page,
                basic_videos=basic_video_list,
                detailed_videos=detailed_video_list,
                has_next=has_next
            )

        except Exception as e:
            logger.exception(f"搜索视频错误: {str(e)}")
            return SearchResults()

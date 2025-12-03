"""
AI Content Generation Service using Google Gemini
"""
from decouple import config
from django.core.exceptions import ValidationError


class AIContentService:
    """Service for AI-powered content generation using Google Gemini"""

    @staticmethod
    def generate_content(
        prompt: str,
        tone: str = 'professional',
        include_hashtags: bool = True,
        include_emoji: bool = True,
        language: str = 'vi'
    ) -> dict:
        """
        Generate post content using Google Gemini AI

        Args:
            prompt: Text prompt describing the content to generate
            tone: Tone of content ('professional', 'casual', 'funny', 'formal')
            include_hashtags: Whether to include hashtags
            include_emoji: Whether to include emojis
            language: Language code ('vi' for Vietnamese, 'en' for English)

        Returns:
            dict: Generated content information
        """
        from google import genai

        # Get API key from settings
        api_key = config('GEMINI_API_KEY', default='')
        if not api_key:
            raise ValidationError("GEMINI_API_KEY is not configured")

        # Initialize Gemini client
        client = genai.Client(api_key=api_key)

        # Get model name from settings
        model_name = config('GEMINI_TEXT_MODEL', default='gemini-2.0-flash')

        # Map tone to Vietnamese instructions
        tone_map = {
            'professional': 'chuyên nghiệp, lịch sự, đáng tin cậy',
            'casual': 'thân thiện, gần gũi, thoải mái',
            'funny': 'hài hước, vui nhộn, dí dỏm',
            'formal': 'trang trọng, nghiêm túc, chính thức'
        }
        tone_instruction = tone_map.get(tone, tone_map['professional'])

        # Build the prompt
        language_instruction = 'tiếng Việt tự nhiên' if language == 'vi' else 'English'
        hashtag_instruction = 'Thêm 3-5 hashtag chiến lược (mix phổ biến + niche) ở cuối bài.' if include_hashtags else 'Không thêm hashtag.'
        emoji_instruction = 'Sử dụng 3-5 emoji phù hợp để tăng tương tác và break text.' if include_emoji else 'Hạn chế emoji.'

        system_prompt = f"""BẠN LÀ CHUYÊN GIA SOCIAL MEDIA MARKETING với hơn 10 năm kinh nghiệm quản lý fanpage cho các thương hiệu lớn tại Việt Nam.

NĂNG LỰC CỦA BẠN:
- Tạo nội dung viral, có tính tương tác cao
- Phân tích insight và tâm lý người dùng Facebook/Instagram
- Tối ưu SEO và thuật toán mạng xã hội
- Viết content thu hút, kết nối cảm xúc với người đọc

NHIỆM VỤ: TẠO BÀI ĐĂNG CHẤT LƯỢNG CAO

Hãy tạo nội dung bài đăng với cấu trúc tối ưu:

1. HOOK (2-3 dòng đầu):
   - Gây chú ý ngay lập tức (quan trọng nhất vì FB cắt preview)
   - Tạo tò mò hoặc cảm xúc mạnh
   - BẮT ĐẦU BÀI VIẾT NGAY với hook, KHÔNG ghi chữ "Hook:"

2. BODY (Nội dung chính):
   - Storytelling hoặc thông tin giá trị
   - Chia đoạn ngắn, dễ đọc (2-3 dòng/đoạn)
   - Tạo kết nối với người đọc
   - CHUYỂN TIẾP TỰ NHIÊN từ hook, KHÔNG ghi chữ "Body:"

3. ENGAGEMENT (Tương tác):
   - Đặt câu hỏi để khuyến khích comment
   - Tạo discussion point
   - VIẾT THẲNG câu hỏi, KHÔNG ghi chữ "Engagement:"

4. CTA (Call-to-Action):
   - Kêu gọi hành động rõ ràng
   - Phù hợp với mục đích bài đăng
   - VIẾT THẲNG lời kêu gọi, KHÔNG ghi chữ "CTA:"

5. HASHTAG:
   - Đặt ở cuối bài, cách 1 dòng trống
   - Mix hashtag phổ biến + niche
   - CHỈ GHI CÁC HASHTAG, KHÔNG ghi chữ "Hashtags:"

=== YÊU CẦU TỪ KHÁCH HÀNG ===
{prompt}

=== HƯỚNG DẪN ===
- Ngôn ngữ: {language_instruction}
- Giọng điệu: {tone_instruction}
- {emoji_instruction}
- {hashtag_instruction}

=== LƯU Ý QUAN TRỌNG ===
- Viết như NGƯỜI THẬT đang chia sẻ, không như robot
- Tạo CẢM XÚC và KẾT NỐI với người đọc
- Tối ưu cho thuật toán Facebook 2024
- Format dễ đọc trên mobile
- QUAN TRỌNG: KHÔNG ĐƯỢC ghi các label như "Hook:", "Body:", "Engagement:", "CTA:", "Hashtags:"
- Nội dung phải CHẢY TỰ NHIÊN từ đầu đến cuối như một bài đăng thật

CHỈ TRẢ VỀ NỘI DUNG BÀI VIẾT HOÀN CHỈNH, KHÔNG GIẢI THÍCH THÊM."""

        try:
            # Generate content using Gemini
            response = client.models.generate_content(
                model=model_name,
                contents=system_prompt
            )

            generated_content = response.text.strip()

            return {
                'content': generated_content,
                'tone': tone,
                'model': model_name,
                'success': True
            }

        except Exception as e:
            raise ValidationError(f"AI content generation failed: {str(e)}")

    @staticmethod
    def generate_hashtags(content: str, count: int = 5) -> dict:
        """
        Generate relevant hashtags for content

        Args:
            content: Post content
            count: Number of hashtags to generate

        Returns:
            dict: Generated hashtags
        """
        from google import genai

        api_key = config('GEMINI_API_KEY', default='')
        if not api_key:
            raise ValidationError("GEMINI_API_KEY is not configured")

        client = genai.Client(api_key=api_key)
        model_name = config('GEMINI_TEXT_MODEL', default='gemini-2.0-flash')

        prompt = f"""
                    Dựa trên nội dung sau, hãy tạo {count} hashtag phù hợp để đăng Facebook:

                    NỘI DUNG:
                    {content}

                    YÊU CẦU:
                    - Tạo {count} hashtag liên quan đến nội dung
                    - Kết hợp hashtag phổ biến và hashtag niche
                    - Mỗi hashtag trên một dòng, bắt đầu bằng dấu #
                    - Không giải thích, chỉ trả về danh sách hashtag
                    """

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            # Parse hashtags from response
            hashtags = []
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    hashtags.append(line)

            return {
                'hashtags': hashtags[:count],
                'model': model_name,
                'success': True
            }

        except Exception as e:
            raise ValidationError(f"Hashtag generation failed: {str(e)}")

    @staticmethod
    def generate_posting_schedule(
        business_type: str,
        goals: str,
        start_date: str,
        duration: str = '1_week',
        posts_per_day: int = 2,
        language: str = 'vi'
    ) -> dict:
        """
        Generate a detailed posting schedule with specific dates and times

        Args:
            business_type: Type of business/industry
            goals: Marketing goals (awareness, engagement, sales, etc.)
            start_date: Start date for the schedule (format: YYYY-MM-DD)
            duration: Schedule duration ('1_week', '2_weeks', '1_month')
            posts_per_day: Number of posts per day
            language: Language code

        Returns:
            dict: Detailed posting schedule with dates and times
        """
        from google import genai
        from datetime import datetime

        api_key = config('GEMINI_API_KEY', default='')
        if not api_key:
            raise ValidationError("GEMINI_API_KEY is not configured")

        client = genai.Client(api_key=api_key)
        model_name = config('GEMINI_TEXT_MODEL', default='gemini-2.0-flash')

        duration_map = {
            '1_week': '7 ngày',
            '2_weeks': '14 ngày',
            '1_month': '30 ngày'
        }
        duration_text = duration_map.get(duration, '7 ngày')

        # Parse start date
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            start_formatted = start.strftime('%d/%m/%Y')
        except:
            start_formatted = start_date

        # Calculate number of days and total posts
        duration_days_map = {
            '1_week': 7,
            '2_weeks': 14,
            '1_month': 30
        }
        total_days = duration_days_map.get(duration, 7)
        total_posts = total_days * posts_per_day

        # Generate random seed for variation
        import random
        variation_seed = random.randint(1000, 9999)

        # Random content type order to avoid fixed patterns
        content_types = ['pain_point', 'educational', 'social_proof', 'engagement', 'conversion', 'lifestyle', 'promo', 'tips', 'behind_the_scenes', 'user_generated', 'trending', 'storytelling']
        random.shuffle(content_types)
        suggested_types = ', '.join(content_types[:7])

        prompt = f"""Bạn là CHUYÊN GIA MARKETING & SOCIAL MEDIA với hơn 10 năm kinh nghiệm quản lý fanpage cho các thương hiệu lớn tại Việt Nam.

=== NHIỆM VỤ: TẠO LỊCH ĐĂNG BÀI JSON FORMAT ===

🎲 VARIATION SEED: {variation_seed} (Dùng seed này để tạo nội dung KHÁC BIỆT hoàn toàn với các lịch khác)

THÔNG TIN:
- Ngành: {business_type}
- Mục tiêu: {goals}
- Ngày bắt đầu: {start_date} (YYYY-MM-DD format)
- Tổng số ngày: {total_days}
- Tổng số bài: {total_posts} bài ({posts_per_day} bài/ngày)

⚠️ QUAN TRỌNG - TRÁNH LẶP LẠI:
- KHÔNG theo pattern cố định (VD: ngày 1 luôn là giới thiệu, ngày 6 luôn là ưu đãi)
- Mỗi lịch trình phải có THỨ TỰ content_type KHÁC NHAU
- Gợi ý thứ tự cho lịch này: {suggested_types}
- Mỗi bài phải có GÓC NHÌN và CHỦ ĐỀ CỤ THỂ khác nhau

YÊU CẦU: Tạo lịch đăng bài ở định dạng JSON với cấu trúc sau:

{{
  "schedule_summary": {{
    "business_type": "{business_type}",
    "duration": "{duration_text}",
    "total_posts": {total_posts},
    "strategy_overview": "Tóm tắt chiến lược content (2-3 câu)"
  }},
  "posts": [
    {{
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "day_of_week": "Thứ 2/3/4/5/6/7/CN",
      "content_type": "pain_point/educational/social_proof/engagement/conversion/lifestyle/promo/tips/behind_the_scenes/trending/storytelling",
      "title": "Tiêu đề CỤ THỂ và HẤP DẪN (VD: '5 lỗi phổ biến khi chọn X', 'Khách hàng A đã tiết kiệm 30% nhờ...')",
      "hook": "3-4 dòng đầu gây SHOCK hoặc TÒ MÒ mạnh, có số liệu hoặc câu hỏi",
      "body": "Nội dung chính 100-150 từ, storytelling hoặc thông tin giá trị CỤ THỂ. Chia đoạn ngắn.",
      "engagement": "Câu hỏi để khuyến khích comment và tương tác",
      "cta": "Kêu gọi hành động rõ ràng (Comment/Share/Save/Click/Inbox)",
      "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
      "media_type": "image/video/carousel/text",
      "goal": "awareness/engagement/conversion/retention"
    }}
  ],
  "hashtag_suggestions": ["#hashtag1", "#hashtag2", ...],
  "engagement_tips": "Tips tăng reach và engagement (2-3 câu)"
}}

LƯU Ý QUAN TRỌNG:
- Tạo ĐÚNG {total_posts} bài đăng, phân bổ đều trong {total_days} ngày
- Mỗi ngày có {posts_per_day} bài, phân bổ thời gian hợp lý (sáng/trưa/chiều/tối)
- Ngày đầu tiên bắt đầu từ {start_date}
- ⚠️ KHÔNG LẶP LẠI PATTERN: Thứ tự content_type phải NGẪU NHIÊN theo gợi ý ở trên
- ⚠️ MỖI BÀI CẦN CHỦ ĐỀ CỤ THỂ: VD thay vì "Tips sử dụng" → "3 sai lầm khi chọn [sản phẩm] khiến bạn mất tiền oan"
- Nội dung hook (3-4 dòng), body (100-150 từ), engagement, cta phải cụ thể, KHÔNG để placeholder
- Hashtags phù hợp với ngành {business_type}
- CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM

Ngôn ngữ nội dung: {'Tiếng Việt' if language == 'vi' else 'English'}"""

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            # Parse JSON response
            import json
            import re

            response_text = response.text.strip()

            # Try to extract JSON from response (AI might wrap it in markdown code blocks)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text

            try:
                schedule_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, return raw text in error
                raise ValidationError(f"AI response is not valid JSON: {str(e)}. Response: {response_text[:500]}")

            # Validate required fields
            if 'posts' not in schedule_data or not isinstance(schedule_data['posts'], list):
                raise ValidationError("AI response missing 'posts' array")

            return {
                'schedule_summary': schedule_data.get('schedule_summary', {}),
                'posts': schedule_data.get('posts', []),
                'hashtag_suggestions': schedule_data.get('hashtag_suggestions', []),
                'engagement_tips': schedule_data.get('engagement_tips', ''),
                'model': model_name,
                'success': True
            }

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Schedule generation failed: {str(e)}")

    @staticmethod
    def generate_content_from_images(
        image_descriptions: list,
        user_prompt: str,
        tone: str = 'casual',
        include_hashtags: bool = True,
        language: str = 'vi'
    ) -> dict:
        """
        Generate high-quality post content based on images and user prompt

        Args:
            image_descriptions: List of image descriptions
            user_prompt: Additional prompt/instructions from user
            tone: Content tone
            include_hashtags: Whether to include hashtags
            language: Language code

        Returns:
            dict: Generated content
        """
        from google import genai

        api_key = config('GEMINI_API_KEY', default='')
        if not api_key:
            raise ValidationError("GEMINI_API_KEY is not configured")

        client = genai.Client(api_key=api_key)
        model_name = config('GEMINI_TEXT_MODEL', default='gemini-2.0-flash')

        # Format image descriptions
        images_text = ""
        for i, desc in enumerate(image_descriptions, 1):
            images_text += f"   Hình {i}: {desc}\n"

        tone_map = {
            'professional': 'chuyên nghiệp, đáng tin cậy',
            'casual': 'thân thiện, gần gũi',
            'funny': 'hài hước, vui nhộn',
            'inspiring': 'truyền cảm hứng, tích cực',
            'emotional': 'cảm xúc, chạm đến trái tim'
        }
        tone_instruction = tone_map.get(tone, tone_map['casual'])

        hashtag_instruction = """
5. HASHTAG (3-5 tags):
   - Mix hashtag phổ biến + niche
   - Đặt ở cuối bài""" if include_hashtags else ""

        prompt = f"""Bạn là CHUYÊN GIA CONTENT MARKETING với khả năng tạo nội dung viral trên Facebook/Instagram.

=== NHIỆM VỤ: TẠO BÀI ĐĂNG CHẤT LƯỢNG CAO ===

HÌNH ẢNH ĐÍNH KÈM:
{images_text}

YÊU CẦU TỪ KHÁCH HÀNG:
{user_prompt}

GIỌNG ĐIỆU: {tone_instruction}
NGÔN NGỮ: {'Tiếng Việt tự nhiên' if language == 'vi' else 'Natural English'}

CẤU TRÚC BÀI VIẾT TỐI ƯU:

1. HOOK (2 dòng đầu - QUAN TRỌNG NHẤT):
   - Gây tò mò/shock/cảm xúc ngay lập tức
   - Liên kết với hình ảnh
   - Khiến người đọc muốn xem tiếp

2. BODY (Nội dung chính):
   - Storytelling kết nối với hình
   - Chia đoạn ngắn (2-3 dòng/đoạn)
   - Highlight điểm nổi bật
   - Tạo value cho người đọc

3. ENGAGEMENT (Tương tác):
   - Đặt câu hỏi để tăng comment
   - Tạo discussion point

4. CTA (Call-to-Action):
   - Kêu gọi hành động rõ ràng
   - Phù hợp với mục đích bài đăng
{hashtag_instruction}

YÊU CẦU FORMAT:
- Sử dụng emoji phù hợp (không spam)
- Line break hợp lý
- Dễ đọc trên mobile
- Độ dài: 100-200 từ

CHỈ TRẢ VỀ NỘI DUNG BÀI VIẾT HOÀN CHỈNH, KHÔNG GIẢI THÍCH."""

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            return {
                'content': response.text.strip(),
                'image_count': len(image_descriptions),
                'tone': tone,
                'model': model_name,
                'success': True
            }

        except Exception as e:
            raise ValidationError(f"Content generation failed: {str(e)}")


class AIImageService:
    """Service for AI-powered image generation using Google Gemini"""

    # Image size configurations
    SIZE_CONFIGS = {
        '1080x1080': (1080, 1080),
        '1200x628': (1200, 628),
        '1080x1920': (1080, 1920),
        '1920x1080': (1920, 1080),
    }

    @staticmethod
    def generate_image(
        prompt: str,
        user,
        size: str,
        creativity: str,
        reference_images: list = None,
        count: int = 3
    ) -> list:
        """
        Generate multiple images using Google Gemini AI

        Args:
            prompt: Text prompt describing the image to generate
            user: User instance
            size: Image size (required) - '1080x1080', '1200x628', '1080x1920', '1920x1080'
            creativity: Creativity level (required) - 'low', 'medium', 'high'
            reference_images: List of reference image file paths (optional)
            count: Number of images to generate (default: 3)

        Returns:
            list: List of generated image information dicts
        """
        import os
        import uuid
        import base64
        import io
        from pathlib import Path
        from PIL import Image
        from django.conf import settings
        from google import genai

        # Get API key from settings
        api_key = config('GEMINI_API_KEY', default='')
        if not api_key:
            raise ValidationError("GEMINI_API_KEY is not configured")

        # Initialize Gemini client
        client = genai.Client(api_key=api_key)

        # Get model name from settings or use default
        model_name = config('GEMINI_IMAGE_MODEL', default='gemini-2.0-flash-preview-image-generation')

        # Map creativity level with detailed instructions
        creativity_instructions = {
            'low': """
- Ưu tiên CHÂN THẬT, THỰC TẾ 100%
- Hình ảnh giống ảnh chụp thật từ máy ảnh/điện thoại
- Tránh hiệu ứng phóng đại hoặc quá hoàn hảo
- Phù hợp với văn hóa và thẩm mỹ Việt Nam
- Màu sắc tự nhiên, ánh sáng tự nhiên""",
            'medium': """
- Cân bằng giữa chân thật và thẩm mỹ
- Có thể tối ưu màu sắc, ánh sáng nhẹ
- Vẫn giữ tính tự nhiên, không quá "ảo"
- Phù hợp đăng Facebook/Instagram Việt Nam
- Có thể thêm chi tiết nhẹ để hấp dẫn hơn""",
            'high': """
- Sáng tạo, nghệ thuật hơn
- Có thể thêm hiệu ứng, màu sắc độc đáo
- Vẫn phải hợp lý và có tính ứng dụng
- Phù hợp với văn hóa Việt Nam
- Thu hút mạnh mẽ trên mạng xã hội"""
        }
        creativity_instruction = creativity_instructions.get(creativity, creativity_instructions['medium'])

        # Map size to Vietnamese description and context
        size_contexts = {
            '1080x1080': 'Vuông (1:1) - Phù hợp Facebook feed, Instagram post',
            '1200x628': 'Banner ngang - Phù hợp Facebook link preview, cover',
            '1080x1920': 'Dọc (9:16) - Phù hợp Instagram/Facebook Story, Reels',
            '1920x1080': 'Ngang (16:9) - Phù hợp YouTube thumbnail, website banner'
        }
        size_context = size_contexts.get(size, 'Square format')

        # Build comprehensive Vietnamese system prompt
        system_prompt = f"""BẠN LÀ CHUYÊN GIA THIẾT KẾ ẢNH CHO MẠNG XÃ HỘI VIỆT NAM
Chuyên tạo hình ảnh chất lượng cao cho Facebook, Instagram, TikTok tại thị trường Việt Nam.

=== NHIỆM VỤ: TẠO ẢNH CHẤT LƯỢNG CHUYÊN NGHIỆP ===

YÊU CẦU TỪ KHÁCH HÀNG:
{prompt}

=== THÔNG SỐ KỸ THUẬT ===
📐 Kích thước: {size_context}
🎨 Mức độ sáng tạo: {creativity.upper()}
{creativity_instruction}

=== NGUYÊN TẮC THIẾT KẾ ===

1. PHONG CÁCH VIỆT NAM:
   - Phù hợp văn hóa, thẩm mỹ người Việt
   - Màu sắc phù hợp khẩu vị thị trường VN
   - Nội dung phù hợp với người dùng mạng xã hội VN
   - Tránh các yếu tố nhạy cảm văn hóa

2. TỐI ƯU CHO MẠNG XÃ HỘI:
   - Bắt mắt ngay lập tức (scroll-stopping)
   - Rõ ràng, dễ nhìn trên mobile
   - Có điểm nhấn (focal point) rõ ràng
   - Phù hợp thuật toán Facebook/Instagram

3. CHẤT LƯỢNG HÌNH ẢNH:
   - Độ phân giải cao, sắc nét
   - Ánh sáng cân bằng, tự nhiên
   - Màu sắc hài hòa, không quá chói
   - Composition chuyên nghiệp

4. NỘI DUNG PHẢI:
   - An toàn, không vi phạm chính sách
   - Tích cực, thu hút tương tác
   - Phù hợp mục đích: bán hàng/marketing/branding
   - Có thể kết hợp text (nếu cần)

5. TRÁNH:
   - Hình ảnh quá ảo, không thực tế
   - Vi phạm bản quyền (logo thương hiệu nổi tiếng)
   - Nội dung nhạy cảm, gây tranh cãi
   - Quá nhiều chi tiết gây rối mắt

=== LƯU Ý ĐẶC BIỆT ===
- Ảnh phải SẠCH, CHUYÊN NGHIỆP, ĐĂNG ĐƯỢC NGAY
- Phù hợp văn hóa và pháp luật Việt Nam
- Tối ưu cho mobile viewing (80% user xem trên điện thoại)
- Có thể dùng làm thumbnail, preview, hoặc ảnh chính

CHỈ TẠO ẢNH THEO YÊU CẦU, KHÔNG GIẢI THÍCH."""

        # Variation prompts để tạo ảnh khác nhau
        variation_instructions = [
            "Tạo phiên bản với GÓC NHÌN/GÓC CHỤP khác biệt, composition độc đáo.",
            "Tạo phiên bản với BỐ CỤC và LIGHTING khác, tạo cảm giác mới mẻ.",
            "Tạo phiên bản với STYLE và CHI TIẾT PHỤ khác, nhưng giữ chủ đề chính.",
            "Tạo phiên bản SÁNG TẠO với màu sắc và hiệu ứng khác biệt.",
            "Tạo phiên bản MINIMALIST hoặc có điểm nhấn khác."
        ]

        generated_images = []
        target_size = AIImageService.SIZE_CONFIGS.get(size, (1080, 1080))
        user_dir = Path(settings.MEDIA_ROOT) / 'uploads' / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)

        for variation_idx in range(count):
            try:
                # Add variation instruction to prompt
                variation_text = variation_instructions[variation_idx % len(variation_instructions)]
                varied_prompt = f"""{system_prompt}

=== VARIATION {variation_idx + 1}/{count} ===
{variation_text}
Đảm bảo ảnh này KHÁC BIỆT với các phiên bản khác nhưng vẫn PHÙ HỢP với yêu cầu gốc."""

                # Build content list
                contents = [varied_prompt]

                # Add reference images if provided
                if reference_images:
                    for img_path in reference_images:
                        try:
                            img = Image.open(img_path)
                            contents.append(img)
                        except Exception as e:
                            print(f"Error loading reference image {img_path}: {e}")

                # Generate image using Gemini
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=genai.types.GenerateContentConfig(
                        response_modalities=['Text', 'Image']
                    )
                )

                # Check if response has candidates
                if not response.candidates:
                    print(f"Variation {variation_idx + 1}: No candidates in response")
                    continue

                candidate = response.candidates[0]

                # Check if candidate was blocked
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                    finish_reason = str(candidate.finish_reason)
                    if 'SAFETY' in finish_reason or 'BLOCK' in finish_reason:
                        print(f"Variation {variation_idx + 1}: Blocked - {finish_reason}")
                        continue

                # Check if content exists
                if not candidate.content or not candidate.content.parts:
                    print(f"Variation {variation_idx + 1}: No content parts")
                    continue

                # Extract ALL images from response parts (không break)
                for part in candidate.content.parts:
                    if part.inline_data is not None:
                        # Decode base64 image data
                        image_data = base64.b64decode(part.inline_data.data)
                        generated_image = Image.open(io.BytesIO(image_data))

                        # Resize to requested size
                        generated_image = generated_image.resize(target_size, Image.Resampling.LANCZOS)

                        # Convert RGBA to RGB if necessary
                        if generated_image.mode == 'RGBA':
                            rgb_img = Image.new('RGB', generated_image.size, (255, 255, 255))
                            rgb_img.paste(generated_image, mask=generated_image.split()[3])
                            generated_image = rgb_img

                        # Save to user's directory
                        filename = f"ai_{uuid.uuid4()}.png"
                        file_path = user_dir / filename
                        generated_image.save(str(file_path), 'PNG', quality=95, optimize=True)

                        # Get file size
                        file_size = os.path.getsize(file_path)

                        generated_images.append({
                            'file_url': f"/media/uploads/{user.id}/{filename}",
                            'file_path': str(file_path),
                            'file_size': file_size,
                            'width': target_size[0],
                            'height': target_size[1],
                            'filename': filename,
                            'variation': variation_idx + 1
                        })

            except Exception as e:
                print(f"Error generating variation {variation_idx + 1}: {str(e)}")
                continue

        if not generated_images:
            raise ValidationError("AI không thể tạo ảnh nào. Vui lòng thử lại với prompt khác.")

        return generated_images

    @staticmethod
    def save_reference_image(file, user) -> str:
        """
        Save reference image temporarily for AI generation

        Args:
            file: Uploaded file
            user: User instance

        Returns:
            str: Path to saved reference image
        """
        import os
        import uuid
        from pathlib import Path
        from django.conf import settings

        # Create temp directory for reference images
        temp_dir = Path(settings.MEDIA_ROOT) / 'temp' / str(user.id)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        filename = f"ref_{uuid.uuid4()}{Path(file.name).suffix}"
        file_path = temp_dir / filename

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return str(file_path)

    @staticmethod
    def cleanup_reference_images(file_paths: list):
        """
        Clean up temporary reference images after generation

        Args:
            file_paths: List of file paths to delete
        """
        import os

        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Error deleting reference image {path}: {e}")

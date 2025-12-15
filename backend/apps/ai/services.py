"""
AI Content Generation Service
Supports multiple AI providers: Google Gemini and DeepSeek
"""
from decouple import config
from django.core.exceptions import ValidationError
import logging
import re

logger = logging.getLogger(__name__)


def clean_markdown_content(content: str) -> str:
    """
    Loại bỏ markdown formatting khỏi content.
    Facebook không hỗ trợ markdown, cần plain text.

    Args:
        content: Nội dung có thể chứa markdown

    Returns:
        Content đã được làm sạch markdown
    """
    if not content:
        return content

    # Remove bold: **text** hoặc __text__
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
    content = re.sub(r'__(.+?)__', r'\1', content)

    # Remove italic: *text* hoặc _text_
    content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', content)
    content = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', content)

    # Remove strikethrough: ~~text~~
    content = re.sub(r'~~(.+?)~~', r'\1', content)

    # Remove inline code: `text`
    content = re.sub(r'`(.+?)`', r'\1', content)

    # Remove markdown headers: # ## ### etc
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

    # Remove markdown links: [text](url) -> text
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)

    # Remove markdown images: ![alt](url)
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)

    # Clean up extra whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


def get_ai_provider() -> str:
    """Get configured AI provider from settings"""
    return config('AI_AGENT_PROVIDER', default='gemini').lower()


def get_text_model_config():
    """
    Get AI client and model name based on configured provider

    Returns:
        tuple: (client, model_name, provider)
    """
    provider = get_ai_provider()

    if provider == 'deepseek':
        from openai import OpenAI
        import httpx

        api_key = config('DEEPSEEK_API_KEY', default='')
        if not api_key:
            raise ValidationError("DEEPSEEK_API_KEY is not configured")

        # Increase timeout for long responses (schedule generation needs more time)
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=httpx.Timeout(120.0, connect=10.0)  # 120s total, 10s connect
        )
        model_name = config('DEEPSEEK_TEXT_MODEL', default='deepseek-chat')

        logger.info(f"[AI] Using DeepSeek provider with model: {model_name}")
        return client, model_name, 'deepseek'

    else:  # Default to Gemini
        from google import genai

        api_key = config('GEMINI_API_KEY', default='')
        if not api_key:
            raise ValidationError("GEMINI_API_KEY is not configured")

        client = genai.Client(api_key=api_key)
        model_name = config('GEMINI_TEXT_MODEL', default='gemini-2.0-flash')

        logger.info(f"[AI] Using Gemini provider with model: {model_name}")
        return client, model_name, 'gemini'


def generate_text_with_provider(prompt: str, client, model_name: str, provider: str, max_tokens: int = None) -> str:
    """
    Generate text using the configured AI provider

    Args:
        prompt: The prompt to send to the AI
        client: AI client instance
        model_name: Model name to use
        provider: Provider name ('gemini' or 'deepseek')
        max_tokens: Maximum tokens for response. If None, uses max available for model.
                    DeepSeek: up to 8192 for deepseek-chat, 16384 for deepseek-reasoner

    Returns:
        str: Generated text response
    """
    if provider == 'deepseek':
        # DeepSeek default max_tokens is low, set high to avoid truncation
        # deepseek-chat supports up to 8192, deepseek-reasoner up to 16384
        if max_tokens is None:
            if 'reasoner' in model_name:
                max_tokens = 16384
            else:
                max_tokens = 8192

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    else:  # Gemini - no max_tokens needed, handles long content well
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text.strip()


class AIContentService:
    """Service for AI-powered content generation - supports Gemini and DeepSeek"""

    @staticmethod
    def generate_content(
        prompt: str,
        tone: str = 'professional',
        include_hashtags: bool = True,
        include_emoji: bool = True,
        language: str = 'vi'
    ) -> dict:
        """
        Generate post content using configured AI provider (Gemini or DeepSeek)

        Args:
            prompt: Text prompt describing the content to generate
            tone: Tone of content ('professional', 'casual', 'funny', 'formal')
            include_hashtags: Whether to include hashtags
            include_emoji: Whether to include emojis
            language: Language code ('vi' for Vietnamese, 'en' for English)

        Returns:
            dict: Generated content information
        """
        # Get AI client based on configured provider
        client, model_name, provider = get_text_model_config()

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

⛔⛔⛔ QUY TẮC BẢO VỆ THƯƠNG HIỆU - BẮT BUỘC TUÂN THỦ:
- TUYỆT ĐỐI KHÔNG viết bất cứ điều gì tiêu cực, bất lợi về sản phẩm/dịch vụ
- KHÔNG nhắc đến điểm yếu, hạn chế, khuyết điểm của sản phẩm
- KHÔNG so sánh tiêu cực với đối thủ
- KHÔNG dùng từ ngữ gây nghi ngờ về chất lượng (có thể, có lẽ, tạm ổn, chấp nhận được...)
- Nội dung phải CHÂN THỰC nhưng luôn TÔN VINH ưu điểm, giá trị của sản phẩm
- Tập trung vào lợi ích khách hàng nhận được, không tập trung vào tính năng khô khan
- Xây dựng NIỀM TIN và SỰ TIN TƯỞNG của khách hàng

CHỈ TRẢ VỀ NỘI DUNG BÀI VIẾT HOÀN CHỈNH, KHÔNG GIẢI THÍCH THÊM."""

        try:
            # Generate content using configured provider
            generated_content = generate_text_with_provider(
                prompt=system_prompt,
                client=client,
                model_name=model_name,
                provider=provider
            )

            # Clean markdown từ content (Facebook không hỗ trợ markdown)
            generated_content = clean_markdown_content(generated_content)

            return {
                'content': generated_content,
                'tone': tone,
                'model': model_name,
                'provider': provider,
                'success': True
            }

        except Exception as e:
            raise ValidationError(f"AI content generation failed: {str(e)}")

    @staticmethod
    def generate_hashtags(content: str, count: int = 5) -> dict:
        """
        Generate relevant hashtags for content using configured AI provider

        Args:
            content: Post content
            count: Number of hashtags to generate

        Returns:
            dict: Generated hashtags
        """
        # Get AI client based on configured provider
        client, model_name, provider = get_text_model_config()

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
            response_text = generate_text_with_provider(
                prompt=prompt,
                client=client,
                model_name=model_name,
                provider=provider
            )

            # Parse hashtags from response
            hashtags = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    hashtags.append(line)

            return {
                'hashtags': hashtags[:count],
                'model': model_name,
                'provider': provider,
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
        Uses configured AI provider (Gemini or DeepSeek)

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
        from datetime import datetime

        # Get AI client based on configured provider
        client, model_name, provider = get_text_model_config()

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
            # Generate schedule using configured provider
            response_text = generate_text_with_provider(
                prompt=prompt,
                client=client,
                model_name=model_name,
                provider=provider
            )

            # Parse JSON response
            import json
            import re

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

            # Check if response looks truncated (incomplete JSON)
            json_str = json_str.strip()
            if not json_str.endswith('}'):
                # Response was truncated - retry with shorter request or raise clear error
                raise ValidationError(
                    f"AI response was truncated (incomplete JSON). "
                    f"Try reducing posts_per_day or duration. "
                    f"Last 100 chars: ...{response_text[-100:]}"
                )

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
                'provider': provider,
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
        Uses configured AI provider (Gemini or DeepSeek)

        Args:
            image_descriptions: List of image descriptions
            user_prompt: Additional prompt/instructions from user
            tone: Content tone
            include_hashtags: Whether to include hashtags
            language: Language code

        Returns:
            dict: Generated content
        """
        # Get AI client based on configured provider
        client, model_name, provider = get_text_model_config()

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
            # Generate content using configured provider
            generated_content = generate_text_with_provider(
                prompt=prompt,
                client=client,
                model_name=model_name,
                provider=provider
            )

            # Clean markdown từ content (Facebook không hỗ trợ markdown)
            generated_content = clean_markdown_content(generated_content)

            return {
                'content': generated_content,
                'image_count': len(image_descriptions),
                'tone': tone,
                'model': model_name,
                'provider': provider,
                'success': True
            }

        except Exception as e:
            raise ValidationError(f"Content generation failed: {str(e)}")


class AIImageService:
    """Service for AI-powered image generation using Google Gemini"""

    # Image size configurations - Facebook optimized 2024
    # Based on Facebook guidelines:
    # - 1080x1080 (1:1): Square, most consistent
    # - 1080x1350 (4:5): Portrait, best for mobile engagement
    # - 1920x1080 (16:9): Landscape, standard video ratio
    # - 1200x628 (1.91:1): Link preview standard
    SIZE_CONFIGS = {
        # Facebook optimized sizes 2024
        '1080x1080': (1080, 1080),   # Square 1:1
        '1080x1350': (1080, 1350),   # Portrait 4:5 - BEST FOR MOBILE
        '1200x628': (1200, 628),     # Link preview 1.91:1
        '1080x1920': (1080, 1920),   # Story 9:16
        '1920x1080': (1920, 1080),   # Landscape 16:9
        # Legacy/other sizes
        '1200x630': (1200, 630),     # Old link preview
        '1000x1000': (1000, 1000),   # Old square
        '2000x1000': (2000, 1000),   # Horizontal wide
        '1000x2000': (1000, 2000),   # Vertical tall
        '1920x960': (1920, 960),     # Horizontal for 4 images
        '960x1920': (960, 1920),     # Vertical for 4 images
        '1920x1920': (1920, 1920),   # Large square
        '1920x1280': (1920, 1280),   # Rectangle for 5 images
    }

    @staticmethod
    def parse_size(size_str: str) -> tuple:
        """
        Parse size string to (width, height) tuple.
        Supports both predefined sizes and custom WIDTHxHEIGHT format.

        Args:
            size_str: Size string like '1080x1080' or '800x600'

        Returns:
            tuple: (width, height) in pixels
        """
        # First check predefined sizes
        if size_str in AIImageService.SIZE_CONFIGS:
            return AIImageService.SIZE_CONFIGS[size_str]

        # Try to parse custom size format WIDTHxHEIGHT
        try:
            if 'x' in size_str.lower():
                parts = size_str.lower().split('x')
                width = int(parts[0].strip())
                height = int(parts[1].strip())

                # Validate reasonable dimensions (min 100, max 4096)
                if 100 <= width <= 4096 and 100 <= height <= 4096:
                    return (width, height)
                else:
                    print(f"Size {size_str} out of range (100-4096), using default")
                    return (1080, 1080)
        except (ValueError, IndexError) as e:
            print(f"Error parsing size {size_str}: {e}")

        # Fallback to default
        return (1080, 1080)

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

        # Convert count to int (callers may pass float like 3.0)
        try:
            count = int(count) if count else 3
        except (ValueError, TypeError):
            count = 3

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
- PHOTOREALISTIC 100% - Ảnh phải trông như chụp từ máy ảnh chuyên nghiệp DSLR/mirrorless
- KHÔNG có đặc điểm AI: không blur kỳ lạ, không texture lặp lại, không finger/hand bất thường
- Ánh sáng TỰ NHIÊN như chụp thật: soft lighting, golden hour, hoặc studio lighting thực tế
- Màu sắc CHÂN THỰC: không quá saturate, không neon, không HDR quá mức
- Chi tiết THỰC TẾ: texture da, vải, kim loại, gỗ... phải như thật
- Bối cảnh THỰC TẾ: như location thật ở Việt Nam (văn phòng, cửa hàng, nhà máy, showroom)
- Sản phẩm trong khung cảnh TỰ NHIÊN, không floating, không background giả tạo
- Nếu có người: tỷ lệ cơ thể đúng, khuôn mặt tự nhiên, biểu cảm thật
- Focus và DOF (depth of field) như ảnh chụp thật""",
            'medium': """
- Cân bằng giữa chân thật và thẩm mỹ cao cấp
- Có thể tối ưu màu sắc, ánh sáng nhẹ nhưng vẫn tự nhiên
- Vẫn giữ tính THỰC TẾ, không quá "ảo" hoặc giả tạo
- Phù hợp đăng Facebook/Instagram Việt Nam
- Chi tiết phải rõ ràng, không bị blur AI điển hình
- Tránh các artifacts của AI như: bàn tay 6 ngón, chữ bị méo, texture lặp lại""",
            'high': """
- Sáng tạo, nghệ thuật hơn nhưng VẪN PHẢI THỰC TẾ
- Có thể thêm hiệu ứng ánh sáng đẹp, màu sắc ấn tượng
- VẪN phải hợp lý và trông như ảnh thật được edit đẹp
- Phù hợp với văn hóa Việt Nam
- Thu hút mạnh mẽ trên mạng xã hội
- Không được trông fake hoặc AI-generated rõ ràng"""
        }
        creativity_instruction = creativity_instructions.get(creativity, creativity_instructions['medium'])

        # Map size to Vietnamese description and context
        size_contexts = {
            '1080x1080': 'Vuông (1:1) - Phù hợp Facebook feed, Instagram post',
            '1080x1350': 'Dọc (4:5) - Tối ưu mobile Facebook/Instagram',
            '1200x628': 'Banner ngang - Phù hợp Facebook link preview, cover',
            '1080x1920': 'Dọc (9:16) - Phù hợp Instagram/Facebook Story, Reels',
            '1920x1080': 'Ngang (16:9) - Phù hợp YouTube thumbnail, website banner',
            # Facebook multi-image post sizes
            '1200x630': 'Banner ngang (1200x630) - Single Facebook post',
            '1000x1000': 'Vuông (1000x1000) - Facebook multi-image post',
            '2000x1000': 'Ngang rộng (2000x1000) - Facebook 2-3 ảnh bố cục ngang',
            '1000x2000': 'Dọc cao (1000x2000) - Facebook 2-3 ảnh bố cục dọc',
            '1920x960': 'Ngang (1920x960) - Facebook 4 ảnh - ảnh header ngang',
            '960x1920': 'Dọc (960x1920) - Facebook 4 ảnh - ảnh header dọc',
            '1920x1920': 'Vuông lớn (1920x1920) - Facebook 4-5 ảnh vuông',
            '1920x1280': 'Chữ nhật (1920x1280) - Facebook 5 ảnh chữ nhật',
            'keep_original': 'Giữ nguyên kích thước ảnh tham chiếu',
        }
        size_context = size_contexts.get(size, f'Kích thước {size}')

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

⚠️ QUAN TRỌNG NHẤT - PHOTOREALISTIC:
   - Ảnh PHẢI trông như CHỤP THẬT từ máy ảnh chuyên nghiệp
   - KHÔNG được trông như ảnh AI tạo ra
   - Chi tiết phải THỰC TẾ 100%: texture, ánh sáng, shadow, reflection
   - Bố cục như ảnh chụp thật, không giả tạo

1. PHONG CÁCH VIỆT NAM:
   - Phù hợp văn hóa, thẩm mỹ người Việt
   - Bối cảnh phải như LOCATION THẬT ở Việt Nam
   - Nội dung phù hợp với người dùng mạng xã hội VN
   - Tránh các yếu tố nhạy cảm văn hóa

2. TỐI ƯU CHO MẠNG XÃ HỘI:
   - Bắt mắt ngay lập tức (scroll-stopping)
   - Rõ ràng, dễ nhìn trên mobile
   - Có điểm nhấn (focal point) rõ ràng
   - Phù hợp thuật toán Facebook/Instagram

3. CHẤT LƯỢNG HÌNH ẢNH (NHƯ ẢNH CHỤP THẬT):
   - Độ phân giải cao, sắc nét như ảnh máy ảnh
   - Ánh sáng TỰ NHIÊN: natural light, golden hour, studio soft light
   - Màu sắc CHÂN THỰC, không over-saturated
   - Composition chuyên nghiệp như nhiếp ảnh gia
   - Depth of field (DOF) và bokeh như ảnh thật
   - Shadow và highlight tự nhiên

4. NỘI DUNG PHẢI:
   - An toàn, không vi phạm chính sách
   - Tích cực, thu hút tương tác
   - Phù hợp mục đích: bán hàng/marketing/branding
   - Sản phẩm/người trong KHUNG CẢNH TỰ NHIÊN

5. TUYỆT ĐỐI TRÁNH (Đặc điểm AI dễ nhận ra):
   - Hình ảnh quá ảo, không thực tế
   - Texture lặp lại hoặc blur kỳ lạ
   - Bàn tay/ngón tay bất thường
   - Chữ/text bị méo hoặc vô nghĩa
   - Background giả tạo, floating objects
   - Ánh sáng/shadow không logic
   - Khuôn mặt "quá hoàn hảo" hoặc méo
   - Vi phạm bản quyền (logo thương hiệu nổi tiếng)
   - Quá nhiều chi tiết gây rối mắt

=== LƯU Ý ĐẶC BIỆT ===
- Ảnh phải SẠCH, CHUYÊN NGHIỆP, ĐĂNG ĐƯỢC NGAY
- Phù hợp văn hóa và pháp luật Việt Nam
- Tối ưu cho mobile viewing (80% user xem trên điện thoại)
- Có thể dùng làm thumbnail, preview, hoặc ảnh chính

⛔⛔⛔ QUY TẮC BẢO VỆ THƯƠNG HIỆU - BẮT BUỘC TUÂN THỦ:
- TUYỆT ĐỐI KHÔNG tạo hình ảnh tiêu cực, bất lợi cho sản phẩm/thương hiệu
- KHÔNG tạo ảnh sản phẩm bị hỏng, bẩn, cũ kỹ, kém chất lượng
- KHÔNG tạo bối cảnh gây cảm giác tiêu cực (u ám, bẩn thỉu, thiếu chuyên nghiệp)
- KHÔNG có yếu tố làm giảm độ tin tưởng của khách hàng
- Sản phẩm phải được thể hiện ĐẸP NHẤT, CHẤT LƯỢNG CAO NHẤT
- Bối cảnh phải SẠCH SẼ, CHUYÊN NGHIỆP, tạo niềm tin
- Hình ảnh phải TÔN VINH giá trị và chất lượng sản phẩm
- Tạo cảm giác CAO CẤP, ĐÁNG TIN CẬY cho thương hiệu

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

        # Handle 'keep_original' - detect size from reference image
        if size == 'keep_original' and reference_images:
            try:
                ref_img = Image.open(reference_images[0])
                target_size = ref_img.size
                ref_img.close()
                print(f"[AI Image] Using reference image size: {target_size}")
            except Exception as e:
                print(f"[AI Image] Could not detect reference size: {e}, using default 1080x1080")
                target_size = (1080, 1080)
        else:
            # Parse size - supports both predefined and custom WIDTHxHEIGHT format
            target_size = AIImageService.parse_size(size)

        user_dir = Path(settings.MEDIA_ROOT) / 'uploads' / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Token tracking for image generation
        total_prompt_tokens = 0
        total_output_tokens = 0
        total_tokens = 0

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

                # Track token usage from this call
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    if hasattr(usage, 'prompt_token_count'):
                        total_prompt_tokens += usage.prompt_token_count or 0
                    if hasattr(usage, 'candidates_token_count'):
                        total_output_tokens += usage.candidates_token_count or 0
                    if hasattr(usage, 'total_token_count'):
                        total_tokens += usage.total_token_count or 0

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

                        # Log original AI-generated size for debugging
                        original_ai_size = generated_image.size
                        print(f"[AI Image] Original from Gemini: {original_ai_size}, Target: {target_size}")

                        # Resize to requested size if different
                        needs_upscale = (target_size[0] > original_ai_size[0] or
                                        target_size[1] > original_ai_size[1])

                        if generated_image.size != target_size:
                            generated_image = generated_image.resize(target_size, Image.Resampling.LANCZOS)

                        # Apply sharpening to improve clarity (especially after upscale)
                        from PIL import ImageFilter, ImageEnhance

                        if needs_upscale:
                            # Stronger sharpening for upscaled images
                            generated_image = generated_image.filter(
                                ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)
                            )
                        else:
                            # Light sharpening for same size or downscaled
                            generated_image = generated_image.filter(
                                ImageFilter.UnsharpMask(radius=1, percent=80, threshold=2)
                            )

                        # Slight contrast boost for more punch
                        enhancer = ImageEnhance.Contrast(generated_image)
                        generated_image = enhancer.enhance(1.05)

                        # Convert RGBA to RGB if necessary
                        if generated_image.mode == 'RGBA':
                            rgb_img = Image.new('RGB', generated_image.size, (255, 255, 255))
                            rgb_img.paste(generated_image, mask=generated_image.split()[3])
                            generated_image = rgb_img

                        # Save as high-quality PNG (lossless, larger file ~3-8MB for high-res images)
                        # PNG compress_level=0 = no compression = maximum quality & larger file
                        filename = f"ai_{uuid.uuid4()}.png"
                        file_path = user_dir / filename
                        generated_image.save(str(file_path), 'PNG', compress_level=0)

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

        # Return images with token usage info
        return {
            'images': generated_images,
            'token_usage': {
                'prompt_tokens': total_prompt_tokens,
                'output_tokens': total_output_tokens,
                'total_tokens': total_tokens
            },
            'model': model_name
        }

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

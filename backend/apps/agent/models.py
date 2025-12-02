"""
Agent App Models
"""
from django.db import models
from apps.auth.models import User
from apps.ai.models import ScheduledContent
from apps.media.models import Media


class AgentPost(models.Model):
    """
    Bài đăng được tạo bởi Agent
    Lưu trữ riêng, không ảnh hưởng code cũ
    """
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # User info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_posts')

    # Source (nếu tạo từ scheduled post)
    scheduled_post = models.ForeignKey(
        ScheduledContent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_generated_posts'
    )

    # Generated content
    content = models.TextField(help_text="Nội dung bài đăng được AI tạo")
    hashtags = models.JSONField(default=list, help_text="Danh sách hashtags")
    full_content = models.TextField(help_text="Content + hashtags đầy đủ")

    # Generated image
    generated_image = models.ForeignKey(
        Media,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_posts'
    )

    # Agent metadata
    agent_reasoning = models.TextField(blank=True, help_text="Lý do và suy nghĩ của agent")
    generation_strategy = models.JSONField(default=dict, help_text="Strategy agent đã dùng")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent Post'
        verbose_name_plural = 'Agent Posts'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Agent Post {self.id} - {self.status}"


class AgentConversation(models.Model):
    """
    Lưu trữ cuộc hội thoại giữa User và Agent
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('agent', 'Agent'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_conversations')

    # Message info
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    message = models.TextField(help_text="Nội dung tin nhắn")

    # Agent action tracking
    function_calls = models.JSONField(
        default=list,
        help_text="Danh sách functions agent đã gọi"
    )

    # Related objects
    related_post = models.ForeignKey(
        AgentPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Agent Conversation'
        verbose_name_plural = 'Agent Conversations'

    def __str__(self):
        return f"{self.role}: {self.message[:50]}"


class AgentPostImage(models.Model):
    """
    Lưu nhiều ảnh cho 1 AgentPost
    Hỗ trợ multi-image generation
    """
    agent_post = models.ForeignKey(
        AgentPost,
        on_delete=models.CASCADE,
        related_name='images'
    )
    media = models.ForeignKey(
        Media,
        on_delete=models.CASCADE,
        related_name='agent_post_images'
    )
    order = models.PositiveIntegerField(default=0, help_text="Thứ tự hiển thị")
    variation = models.PositiveIntegerField(default=1, help_text="Variation number từ AI")

    class Meta:
        ordering = ['order']
        verbose_name = 'Agent Post Image'
        verbose_name_plural = 'Agent Post Images'

    def __str__(self):
        return f"Image {self.order} for Post {self.agent_post_id}"


class AgentTask(models.Model):
    """
    Tracking các tasks agent đang làm
    """
    TASK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    TASK_TYPE_CHOICES = [
        ('generate_post', 'Generate Post'),
        ('analyze_schedule', 'Analyze Schedule'),
        ('check_system', 'Check System'),
        ('custom', 'Custom Task'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_tasks')

    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES)
    description = models.TextField(help_text="Mô tả task")

    # Status
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0, help_text="0-100")

    # Result
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Related objects
    related_post = models.ForeignKey(
        AgentPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent Task'
        verbose_name_plural = 'Agent Tasks'

    def __str__(self):
        return f"{self.task_type} - {self.status}"

"""
AI App Models
"""
from django.db import models
from django.utils import timezone
from apps.auth.models import User


class PostingSchedule(models.Model):
    """
    Model to store posting schedule information
    A schedule can contain multiple posts
    """
    # Foreign Keys
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posting_schedules')

    # Schedule Information
    business_type = models.CharField(max_length=255)
    goals = models.TextField(help_text="Marketing goals for this schedule")
    start_date = models.DateField()
    duration = models.CharField(max_length=20)  # 1_week, 2_weeks, 1_month
    posts_per_day = models.IntegerField(default=2)
    total_posts = models.IntegerField()

    # AI Strategy
    strategy_overview = models.TextField(blank=True)
    hashtag_suggestions = models.JSONField(default=list)
    engagement_tips = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Posting Schedule'
        verbose_name_plural = 'Posting Schedules'

    def __str__(self):
        return f"{self.business_type} - {self.start_date} ({self.duration})"


class ScheduledContent(models.Model):
    """
    Model to store AI-generated scheduled posts
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('pain_point', 'Pain Point'),
        ('educational', 'Educational'),
        ('social_proof', 'Social Proof'),
        ('engagement', 'Engagement'),
        ('conversion', 'Conversion'),
        ('lifestyle', 'Lifestyle'),
        ('promo', 'Promotion'),
    ]

    MEDIA_TYPE_CHOICES = [
        ('text', 'Text Only'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('carousel', 'Carousel'),
    ]

    GOAL_CHOICES = [
        ('awareness', 'Awareness'),
        ('engagement', 'Engagement'),
        ('conversion', 'Conversion'),
        ('retention', 'Retention'),
    ]

    # Foreign Keys
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_contents')
    schedule = models.ForeignKey(PostingSchedule, on_delete=models.CASCADE, related_name='posts', null=True, blank=True)

    # Schedule Information
    business_type = models.CharField(max_length=255)
    schedule_date = models.DateField()
    schedule_time = models.TimeField()
    day_of_week = models.CharField(max_length=20)  # Thứ 2, Thứ 3, etc.

    # Content Classification
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    goal = models.CharField(max_length=50, choices=GOAL_CHOICES)

    # Content Sections
    hook = models.TextField(help_text="Opening hook (2 lines)")
    body = models.TextField(help_text="Main content body")
    engagement = models.TextField(help_text="Engagement question")
    cta = models.TextField(help_text="Call to action")
    hashtags = models.JSONField(default=list, help_text="List of hashtags")

    # Media
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES, default='text')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['schedule_date', 'schedule_time']
        verbose_name = 'Scheduled Content'
        verbose_name_plural = 'Scheduled Contents'

    def __str__(self):
        return f"{self.schedule_date} {self.schedule_time} - {self.title}"

    @property
    def full_content(self):
        """Generate full post content"""
        content_parts = [
            self.hook,
            "",  # Empty line
            self.body,
            "",  # Empty line
            self.engagement,
            "",  # Empty line
            self.cta,
        ]

        if self.hashtags:
            content_parts.append("")  # Empty line
            content_parts.append(" ".join(self.hashtags))

        return "\n".join(content_parts)


class AsyncAITask(models.Model):
    """
    Model to track async AI generation tasks with time statistics
    """
    TASK_TYPE_CHOICES = [
        ('content', 'Content Generation'),
        ('image', 'Image Generation'),
        ('schedule', 'Schedule Generation'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Task Identification
    task_id = models.CharField(max_length=100, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_tasks')
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)

    # Task Parameters (stored as JSON)
    input_params = models.JSONField(help_text="Task input parameters")

    # Task Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")

    # Task Result
    result = models.JSONField(null=True, blank=True, help_text="Task result data")
    error_message = models.TextField(null=True, blank=True)

    # Time Tracking for Statistics
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True, help_text="Total execution time in seconds")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Async AI Task'
        verbose_name_plural = 'Async AI Tasks'
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.task_type} - {self.task_id} ({self.status})"

    def mark_started(self):
        """Mark task as started and record start time"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, result_data):
        """Mark task as completed and calculate duration"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.result = result_data

        if self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.duration_seconds = duration

        self.save(update_fields=['status', 'completed_at', 'result', 'duration_seconds'])

    def mark_failed(self, error_msg):
        """Mark task as failed and record error"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_msg

        if self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.duration_seconds = duration

        self.save(update_fields=['status', 'completed_at', 'error_message', 'duration_seconds'])

    def update_progress(self, progress_value):
        """Update task progress percentage"""
        self.progress = min(100, max(0, progress_value))
        self.save(update_fields=['progress'])

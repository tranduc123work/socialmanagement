from django.db import models


class Media(models.Model):
    MEDIA_TYPES = [('image', 'Image'), ('video', 'Video')]

    user = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE, related_name='media')
    file_url = models.URLField()
    file_path = models.CharField(max_length=500, help_text='Absolute path to file on disk')
    file_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    file_size = models.IntegerField()
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    folder = models.ForeignKey('MediaFolder', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media'
        ordering = ['-created_at']


class MediaFolder(models.Model):
    user = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_folders'


class MediaTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    media = models.ManyToManyField(Media, related_name='tags')

    class Meta:
        db_table = 'media_tags'

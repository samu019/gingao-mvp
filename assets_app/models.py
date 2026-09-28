from django.conf import settings
from django.db import models
class Asset(models.Model):
    TYPES=[('image','Image'),('video','Video'),('audio','Audio'),('character','Character')]
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='assets')
    kind=models.CharField(max_length=16,choices=TYPES)
    name=models.CharField(max_length=160)
    file=models.FileField(upload_to='assets/%Y/%m/',blank=True)
    source_url=models.URLField(blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

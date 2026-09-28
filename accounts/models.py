from django.contrib.auth.models import AbstractUser
from django.db import models
class User(AbstractUser):
    is_internal_admin = models.BooleanField(default=False)
    plan_code = models.CharField(max_length=32, default='free')

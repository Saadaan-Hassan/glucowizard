from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Keep it simple; extend later
    email = models.EmailField(blank=True, null=True, unique=False)

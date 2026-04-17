from datetime import datetime
import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission, Group
from django.db.models import Q
from django.db.models import F
from django.db.models import Sum
import re
from django.contrib.auth.password_validation import validate_password

class Command(BaseCommand):
    def handle(self, *args, **options):
        user = User.objects.create(
            username='superadmin',
            is_superuser=True,
            is_staff=True,
            first_name='Admin',
            last_name='S'
        )
        user.set_password('admin')
        user.save()

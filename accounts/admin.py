from django.contrib import admin
from .models import User, PasswordHistory, AuditLog

# Register your models here.
admin.site.register(User)
admin.site.register(PasswordHistory)
admin.site.register(AuditLog)
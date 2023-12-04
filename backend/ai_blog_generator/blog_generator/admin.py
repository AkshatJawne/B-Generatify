from django.contrib import admin
from .models import BlogPost


# Register blogpost model to Django Admin page
admin.site.register(BlogPost)

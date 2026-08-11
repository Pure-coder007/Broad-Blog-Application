from rest_framework import serializers
from .models import Post


class PostSerializer(serializers.ModelSerializer):
    # Validating title length
    title = serializers.CharField(max_length=50)
    author = serializers.ReadOnlyField(source="author.username")
    

    class Meta:
        model = Post
        fields = ["id", "title", "content", "author", "views", "created", "updated"]
        read_only_fields = ["id", "author", "views", "created", "updated"]

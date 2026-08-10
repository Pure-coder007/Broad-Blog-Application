import django_filters
from .models import Post


class PostFilter(django_filters.FilterSet):
    author = django_filters.CharFilter(
        field_name="author__username",
        lookup_expr="iexact",
    )

    title = django_filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
    )

    content = django_filters.CharFilter(
        field_name="content",
        lookup_expr="icontains",
    )

    created_after = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="lte",
    )
    
    class Meta:
        model = Post
        fields = ["author", "title", "content", "created_after", "created_before"]

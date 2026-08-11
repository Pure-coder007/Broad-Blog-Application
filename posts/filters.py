import django_filters
from .models import Post
from django import forms
from django.core.exceptions import ValidationError





class PostFilterForm(forms.Form):

    views_min = forms.IntegerField(
        required=False,
        min_value=0,
    )

    views_max = forms.IntegerField(
        required=False,
        min_value=0,
    )

    def clean(self):

        cleaned_data = super().clean()

        views_min = cleaned_data.get("views_min")
        views_max = cleaned_data.get("views_max")

        if (
            views_min is not None
            and views_max is not None
            and views_min > views_max
        ):
            raise forms.ValidationError(
                "Minimum views cannot be greater than maximum views."
            )

        return cleaned_data







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
    
    # Minimum views
    views_min = django_filters.NumberFilter(
        field_name="views",
        lookup_expr="gte",
        min_value=0,
    )
    
    # Maximum views
    views_max = django_filters.NumberFilter(
        field_name="views",
        lookup_expr="lte",
        min_value=0,
        
    )
    
    is_published = django_filters.BooleanFilter(
        field_name="is_published",
        
    )
    
    popular = django_filters.BooleanFilter(
        method="filter_popular"
    )
    
    class Meta:
        model = Post
        fields = ["author", "title", "content", "created_after", "created_before", "views_min", "views_max", "is_published", "popular"]
        
        form = PostFilterForm

    def filter_popular(self, queryset, name, value):
        if value is True:
            return queryset.filter(views__gte=1000)

        if value is False:
            return queryset.filter(views__lt=1000)
        
        return queryset



    # def clean(self):
    #     cleaned_data = super().clean()
        
    #     views_min = cleaned_data.get("views_min")
    #     views_max = cleaned_data.get("views_max")
        
    #     if (views_min is not None and views_max is not None and views_min > views_max):
    #         raise django_filters.ValidationError("Minimum views cannot be greater than maximum views.")
        
    #     return cleaned_data
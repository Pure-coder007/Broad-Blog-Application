from django.urls import path
from .views import (
    PostListCreateView,
    PostRetrieveUpdateDeleteView,
    homepage,
    ListPostForAuthorView,
)

urlpatterns = [
    path("homepage/", homepage.as_view(), name="homepage"),
    path("", PostListCreateView.as_view(), name="post-list-create"),
    path("<uuid:pk>/", PostRetrieveUpdateDeleteView.as_view(), name="post-detail"),
    path("posts_for_current_user/", ListPostForAuthorView.as_view(), name="posts"),
]

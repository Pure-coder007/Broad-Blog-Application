from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status, generics, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Post
from .serializers import PostSerializer
from .permissions import ReadOnly, AuthorOrReadOnly
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import ScopedRateThrottle


# ============================================================
# CLASS-BASED VIEWS (ACTIVE)
# ============================================================


class homepage(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, *args, **kwargs):
        return Response({
            "message": "Welcome to the SimpleGlog API"
        }, status=status.HTTP_200_OK)


class PostListCreateView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
):
    # Rate limiting settings
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "posts"
    
    """
    Handles listing all posts and creating a new post.
    """
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    # permission_classes = [AuthorOrReadOnly]
    queryset = Post.objects.all().order_by("-created")

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Search functionality
        search = request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search)
            )

        # Ordering functionality
        ordering = request.query_params.get("ordering")

        allowed_orderings = [
            "created",
            "-created",
            "title",
            "-title",
            "author__username",
            "-author__username",
            "content",
            "-content"
        ]

        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created")

        # Filtering functionality
        author = request.query_params.get("author")
        title = request.query_params.get("title")

        if author:
            queryset = queryset.filter(
                author__username=author
            )

        if title:
            queryset = queryset.filter(
                title__icontains=title
            )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request: Request, *args, **kwargs):
        """
        Create a new post.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response({
                "message": "Post created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PostRetrieveUpdateDeleteView(
    generics.GenericAPIView,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    """
    Handles retrieving, updating, and deleting a single post.
    """
    serializer_class = PostSerializer
    permission_classes = [AuthorOrReadOnly]
    queryset = Post.objects.all()
    lookup_field = "pk"

    def get(self, request: Request, *args, **kwargs):
        """
        Get a single post by ID.
        """
        post = self.get_object()
        serializer = self.get_serializer(post)
        return Response({
            "message": "Post retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request: Request, *args, **kwargs):
        """
        Fully update a post.
        """
        post = self.get_object()
        serializer = self.get_serializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Post updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request: Request, *args, **kwargs):
        """
        Partially update a post.
        """
        post = self.get_object()
        serializer = self.get_serializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Post partially updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request: Request, *args, **kwargs):
        """
        Delete a post by ID.
        """
        post = self.get_object()
        post.delete()
        return Response({
            "message": "Post deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)


class ListPostForAuthorView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# ============================================================
# FUNCTION-BASED VIEWS (COMMENTED OUT - NOT IN USE)
# ============================================================

# from rest_framework.decorators import api_view, permission_classes
#
# @api_view(['GET', 'POST'])
# @permission_classes([IsAuthenticated])
# def post_list_create(request):
#     """
#     Function-based view for listing and creating posts.
#     """
#     if request.method == 'GET':
#         posts = Post.objects.all()
#         search = request.query_params.get('search', None)
#         if search:
#             posts = posts.filter(
#                 Q(title__icontains=search) |
#                 Q(content__icontains=search)
#             )
#         serializer = PostSerializer(posts, many=True)
#         return Response({
#             "message": "All posts retrieved successfully",
#             "count": posts.count(),
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)
#
#     elif request.method == 'POST':
#         serializer = PostSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save(author=request.user)
#             return Response({
#                 "message": "Post created successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_201_CREATED)
#         return Response({
#             "message": "Validation failed",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#
# @api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
# @permission_classes([IsAuthenticated])
# def post_detail(request, pk):
#     """
#     Function-based view for retrieving, updating, and deleting a post.
#     """
#     post = get_object_or_404(Post, pk=pk)
#
#     if request.method == 'GET':
#         serializer = PostSerializer(post)
#         return Response({
#             "message": "Post retrieved successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)
#
#     elif request.method == 'PUT':
#         serializer = PostSerializer(post, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({
#                 "message": "Post updated successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_200_OK)
#         return Response({
#             "message": "Validation failed",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#     elif request.method == 'PATCH':
#         serializer = PostSerializer(post, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({
#                 "message": "Post partially updated successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_200_OK)
#         return Response({
#             "message": "Validation failed",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#     elif request.method == 'DELETE':
#         post.delete()
#         return Response({
#             "message": "Post deleted successfully"
#         }, status=status.HTTP_204_NO_CONTENT)


# ============================================================
# VIEWSETS (COMMENTED OUT - NOT IN USE)
# ============================================================

# from rest_framework import viewsets
# from rest_framework.decorators import action
#
# class PostViewSet(viewsets.ModelViewSet):
#     """
#     Complete ViewSet with all CRUD operations.
#     """
#     queryset = Post.objects.all()
#     serializer_class = PostSerializer
#     permission_classes = [IsAuthenticated]
#
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         search = request.query_params.get('search', None)
#         if search:
#             queryset = queryset.filter(
#                 Q(title__icontains=search) |
#                 Q(content__icontains=search)
#             )
#         serializer = self.get_serializer(queryset, many=True)
#         return Response({
#             "message": "All posts retrieved successfully",
#             "count": queryset.count(),
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save(author=request.user)
#             return Response({
#                 "message": "Post created successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_201_CREATED)
#         return Response({
#             "message": "Validation failed",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
#         return Response({
#             "message": "Post retrieved successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)
#
#     def update(self, request, *args, **kwargs):
#         partial = kwargs.pop('partial', False)
#         instance = self.get_object()
#         serializer = self.get_serializer(instance, data=request.data, partial=partial)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({
#                 "message": "Post updated successfully",
#                 "data": serializer.data
#             }, status=status.HTTP_200_OK)
#         return Response({
#             "message": "Validation failed",
#             "errors": serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         instance.delete()
#         return Response({
#             "message": "Post deleted successfully"
#         }, status=status.HTTP_204_NO_CONTENT)
#
#     @action(detail=True, methods=['post'])
#     def publish(self, request, pk=None):
#         post = self.get_object()
#         post.is_published = True
#         post.save()
#         serializer = self.get_serializer(post)
#         return Response({
#             "message": "Post published successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)
#
#     @action(detail=False, methods=['get'])
#     def my_posts(self, request):
#         posts = self.get_queryset().filter(author=request.user)
#         serializer = self.get_serializer(posts, many=True)
#         return Response({
#             "message": "Your posts retrieved successfully",
#             "count": posts.count(),
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)

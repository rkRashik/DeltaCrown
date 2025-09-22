"""
Team Social Features URLs
"""
from django.urls import path
from .views import social

app_name = 'teams_social'

urlpatterns = [
    # Team social detail page
    path('<slug:team_slug>/social/', social.team_social_detail, name='team_social_detail'),
    
    # Post management
    path('<slug:team_slug>/posts/create/', social.create_team_post, name='create_post'),
    path('<slug:team_slug>/posts/<int:post_id>/edit/', social.edit_team_post, name='edit_post'),
    path('<slug:team_slug>/posts/<int:post_id>/delete/', social.delete_team_post, name='delete_post'),
    path('<slug:team_slug>/posts/<int:post_id>/media/<int:media_id>/delete/', social.delete_post_media, name='delete_post_media'),
    path('<slug:team_slug>/posts/<int:post_id>/comment/', social.create_post_comment, name='create_comment'),
    path('<slug:team_slug>/posts/<int:post_id>/like/', social.toggle_post_like, name='toggle_like'),
    
    # Team following
    path('<slug:team_slug>/follow/', social.toggle_team_follow, name='toggle_follow'),
    
    # Banner upload
    path('<slug:team_slug>/banner/upload/', social.upload_team_banner, name='upload_banner'),
    
    # AJAX endpoints
    path('<slug:team_slug>/posts/feed/', social.team_posts_feed, name='posts_feed'),
    path('<slug:team_slug>/activity/', social.team_activity_feed, name='activity_feed'),
]
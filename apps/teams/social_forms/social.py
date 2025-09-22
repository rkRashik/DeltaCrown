"""
Team Social Features Forms
"""
from django import forms
from django.core.exceptions import ValidationError
from ..models.social import TeamPost, TeamPostComment, TeamPostMedia
from django.utils.html import strip_tags


class TeamPostForm(forms.ModelForm):
    """Form for creating and editing team posts."""
    
    class Meta:
        model = TeamPost
        fields = ['title', 'content', 'post_type', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What\'s on your mind?',
                'maxlength': 200
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share something with your community...'
            }),
            'post_type': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.author = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)
        
        # Customize visibility choices based on team settings
        if self.team:
            visibility_choices = [
                ('public', 'Public - Anyone can see'),
                ('followers', 'Followers - Only team followers'),
                ('members', 'Members - Only team members')
            ]
            self.fields['visibility'].choices = visibility_choices
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            # Clean HTML and limit length  
            content = strip_tags(content)
            if len(content) > 5000:
                raise ValidationError("Content is too long (maximum 5000 characters).")
        return content
    
    def save(self, commit=True):
        post = super().save(commit=False)
        if self.team:
            post.team = self.team
        if self.author:
            post.author = self.author
        # Set published_at to current time for immediate publication
        if not post.published_at:
            from django.utils import timezone
            post.published_at = timezone.now()
        if commit:
            post.save()
        return post


class TeamPostCommentForm(forms.ModelForm):
    """Form for creating team post comments."""
    
    class Meta:
        model = TeamPostComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Write a comment...',
                'maxlength': 1000
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop('post', None)
        self.author = kwargs.pop('author', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            content = strip_tags(content)
            if len(content.strip()) < 3:
                raise ValidationError("Comment is too short (minimum 3 characters).")
        return content
    
    def save(self, commit=True):
        comment = super().save(commit=False)
        if self.post:
            comment.post = self.post
        if self.author:
            comment.author = self.author
        if self.parent:
            comment.parent = self.parent
        if commit:
            comment.save()
        return comment


class TeamPostMediaForm(forms.ModelForm):
    """Form for uploading media to team posts."""
    
    class Meta:
        model = TeamPostMedia
        fields = ['file', 'alt_text']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,video/*'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describe this image...',
                'maxlength': 200
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop('post', None)
        super().__init__(*args, **kwargs)
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 
                           'video/mp4', 'video/webm']
            if hasattr(file, 'content_type') and file.content_type not in allowed_types:
                raise ValidationError("Unsupported file type. Please use images or videos.")
        return file
    
    def save(self, commit=True):
        media = super().save(commit=False)
        if self.post:
            media.post = self.post
        if commit:
            media.save()
        return media


class TeamFollowForm(forms.Form):
    """Simple form for following/unfollowing teams."""
    
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)
    
    def toggle_follow(self):
        """Toggle follow status and return new status."""
        if not self.team or not self.user_profile:
            return False
        
        from ..models.social import TeamFollower
        
        follower, created = TeamFollower.objects.get_or_create(
            team=self.team,
            follower=self.user_profile
        )
        
        if not created:
            # Already following, so unfollow
            follower.delete()
            return False
        return True


class TeamBannerForm(forms.Form):
    """Form for uploading team banner image."""
    
    banner_image = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
    
    def clean_banner_image(self):
        image = self.cleaned_data.get('banner_image')
        if image:
            # Check file size (5MB limit for banners)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Banner image cannot exceed 5MB.")
            
            # Check dimensions (recommended: 1200x400)
            from PIL import Image
            try:
                img = Image.open(image)
                width, height = img.size
                
                # Minimum dimensions
                if width < 800 or height < 200:
                    raise ValidationError("Banner image must be at least 800x200 pixels.")
                
                # Aspect ratio check (should be roughly 3:1)
                ratio = width / height
                if ratio < 2.5 or ratio > 4.0:
                    raise ValidationError("Banner image should have a wide aspect ratio (recommended: 3:1).")
                    
            except Exception as e:
                raise ValidationError("Invalid image file.")
        
        return image
    
    def save(self):
        """Save the banner image to the team."""
        if self.team and 'banner_image' in self.cleaned_data:
            self.team.banner_image = self.cleaned_data['banner_image']
            self.team.save(update_fields=['banner_image'])
            return self.team
        return None
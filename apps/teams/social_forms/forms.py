"""
Custom Forms for Team Social Features
"""
from django import forms
from ..models import Team
from ..models.social import TeamPost, TeamPostComment
from apps.user_profile.models import UserProfile

class TeamPostForm(forms.ModelForm):
    """Form for creating a team post."""
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Share something with your team...'}),
        label=""
    )

    class Meta:
        model = TeamPost
        fields = ['content']

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.author = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        post = super().save(commit=False)
        post.team = self.team
        post.author = self.author
        if commit:
            post.save()
        return post

class TeamPostCommentForm(forms.ModelForm):
    """Form for commenting on a team post."""
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Write a comment...'}),
        label=""
    )

    class Meta:
        model = TeamPostComment
        fields = ['content']

    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop('post', None)
        self.author = kwargs.pop('author', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        comment = super().save(commit=False)
        comment.post = self.post
        comment.author = self.author
        if self.parent:
            comment.parent = self.parent
        if commit:
            comment.save()
        return comment

class TeamFollowForm(forms.Form):
    """Empty form to handle team following/unfollowing."""
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)

class TeamBannerForm(forms.Form):
    """Form for uploading a new team banner."""
    banner = forms.ImageField(label="Upload New Banner")

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

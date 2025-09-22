"""
Community Post Forms
"""
from django import forms
from .models import CommunityPost, CommunityPostComment, CommunityPostMedia


class CommunityPostForm(forms.ModelForm):
    """Form for creating and editing community posts"""
    
    class Meta:
        model = CommunityPost
        fields = ['title', 'content', 'game', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Add a title to your post (optional)...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': "What's happening in your gaming world?",
                'rows': 4
            }),
            'game': forms.Select(attrs={
                'class': 'form-select'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Game choices from available games
        game_choices = [('', 'Select a game (optional)')] + [
            ('valorant', 'Valorant'),
            ('efootball', 'eFootball'),
            ('cs2', 'Counter-Strike 2'),
            ('fc26', 'FC 26'),
            ('pubg', 'PUBG'),
            ('mobile_legends', 'Mobile Legends'),
        ]
        self.fields['game'].widget = forms.Select(
            choices=game_choices,
            attrs={'class': 'form-select'}
        )
        
        # Make title not required
        self.fields['title'].required = False
        self.fields['game'].required = False


class CommunityPostCommentForm(forms.ModelForm):
    """Form for creating comments on community posts"""
    
    class Meta:
        model = CommunityPostComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'comment-textarea',
                'placeholder': 'Write a comment...',
                'rows': 2
            })
        }


class CommunityPostMediaForm(forms.ModelForm):
    """Form for uploading media to community posts"""
    
    class Meta:
        model = CommunityPostMedia
        fields = ['file', 'alt_text', 'media_type']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*,video/*,.gif'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Describe this media (optional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alt_text'].required = False


# Multiple file upload form - Use basic Input widget instead of FileInput
class MultipleFileInput(forms.Widget):
    """Custom widget for multiple file uploads"""
    
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        # Don't call super().__init__ with multiple=True to avoid Django's validation
        super().__init__(attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs['type'] = 'file'
        attrs['multiple'] = True
        attrs['name'] = name
        
        # Build the HTML input element
        final_attrs = self.build_attrs(self.attrs, attrs)
        if value:
            final_attrs['value'] = value
            
        html_attrs = []
        for key, val in final_attrs.items():
            if val is not None:
                if val is True:
                    html_attrs.append(f'{key}')
                else:
                    html_attrs.append(f'{key}="{val}"')
        
        return f'<input {" ".join(html_attrs)} />'
    
    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        else:
            file_list = files.get(name)
            return [file_list] if file_list else []

class MultipleFileField(forms.Field):
    """Field for handling multiple file uploads"""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data):
        if not data:
            return []
        
        if not isinstance(data, (list, tuple)):
            data = [data]
        
        result = []
        for file_data in data:
            if file_data:
                # Basic file validation
                if hasattr(file_data, 'content_type'):
                    # Check file size (10MB limit)
                    if file_data.size > 10 * 1024 * 1024:
                        raise forms.ValidationError(f"File {file_data.name} is too large. Maximum size is 10MB.")
                    
                    # Check file type
                    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/webm']
                    if file_data.content_type not in allowed_types:
                        raise forms.ValidationError(f"File type {file_data.content_type} is not supported.")
                
                result.append(file_data)
        
        return result

class CommunityPostCreateForm(forms.ModelForm):
    """Enhanced form with multiple file upload support"""
    # We'll handle media files manually in the view instead of using a form field
    
    class Meta:
        model = CommunityPost
        fields = ['title', 'content', 'game', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Add a title to your post (optional)...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': "What's happening in your gaming world?",
                'rows': 4
            }),
            'game': forms.Select(attrs={
                'class': 'form-select'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Game choices
        game_choices = [('', 'Select a game (optional)')] + [
            ('valorant', 'Valorant'),
            ('efootball', 'eFootball'),
            ('cs2', 'Counter-Strike 2'),
            ('fc26', 'FC 26'),
            ('pubg', 'PUBG'),
            ('mobile_legends', 'Mobile Legends'),
        ]
        self.fields['game'].widget = forms.Select(
            choices=game_choices,
            attrs={'class': 'form-select'}
        )
        
        # Optional fields
        self.fields['title'].required = False
        self.fields['game'].required = False
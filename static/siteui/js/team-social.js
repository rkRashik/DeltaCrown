/**
 * Team Social Features - Interactive JavaScript
 * Facebook-like functionality for team social pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize social features
    initializeLikeButtons();
    initializeCommentForms();
    initializeFollowButton();
    initializeLoadMore();
    initializeMediaPreview();
    initializePostCreation();
});

/**
 * Like/Unlike functionality with AJAX
 */
function initializeLikeButtons() {
    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            
            const postId = this.dataset.postId;
            const teamSlug = getTeamSlugFromURL();
            
            if (!postId || !teamSlug) return;
            
            // Optimistic UI update
            const isLiked = this.classList.contains('text-danger');
            const heartIcon = this.querySelector('i');
            const likeText = this.querySelector('.like-text') || this;
            
            // Toggle visual state immediately
            if (isLiked) {
                this.classList.remove('text-danger');
                this.classList.add('text-muted');
                heartIcon.classList.remove('fas');
                heartIcon.classList.add('far');
            } else {
                this.classList.remove('text-muted');
                this.classList.add('text-danger');
                heartIcon.classList.remove('far');
                heartIcon.classList.add('fas');
            }
            
            try {
                const response = await fetch(`/teams/${teamSlug}/posts/${postId}/like/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    // Update like count
                    const likeCount = document.querySelector(`[data-post-id="${postId}"] .likes-count`);
                    if (likeCount) {
                        const count = data.like_count;
                        likeCount.innerHTML = `<i class="fas fa-heart text-danger"></i> ${count} ${count === 1 ? 'like' : 'likes'}`;
                    }
                    
                    // Animate like action
                    if (data.liked) {
                        animateHeartLike(heartIcon);
                    }
                } else {
                    // Revert optimistic update on error
                    if (isLiked) {
                        this.classList.add('text-danger');
                        this.classList.remove('text-muted');
                        heartIcon.classList.add('fas');
                        heartIcon.classList.remove('far');
                    } else {
                        this.classList.add('text-muted');
                        this.classList.remove('text-danger');
                        heartIcon.classList.add('far');
                        heartIcon.classList.remove('fas');
                    }
                }
            } catch (error) {
                console.error('Error toggling like:', error);
                // Revert on error
                if (isLiked) {
                    this.classList.add('text-danger');
                    this.classList.remove('text-muted');
                } else {
                    this.classList.add('text-muted');
                    this.classList.remove('text-danger');
                }
            }
        });
    });
}

/**
 * Comment form submission with AJAX
 */
function initializeCommentForms() {
    document.querySelectorAll('.add-comment-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const postId = this.dataset.postId;
            const teamSlug = getTeamSlugFromURL();
            const contentInput = this.querySelector('input[name="content"]');
            const content = contentInput.value.trim();
            
            if (!content || !postId || !teamSlug) return;
            
            // Disable form during submission
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalHTML = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            submitBtn.disabled = true;
            
            try {
                const formData = new FormData();
                formData.append('content', content);
                formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
                
                const response = await fetch(`/teams/${teamSlug}/posts/${postId}/comment/`, {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.success) {
                        // Clear input
                        contentInput.value = '';
                        
                        // Add new comment to the list
                        addCommentToList(postId, data);
                        
                        // Update comment count
                        updateCommentCount(postId, 1);
                        
                        // Show success animation
                        showSuccessAnimation(submitBtn);
                    } else {
                        showError('Failed to post comment');
                    }
                } else {
                    showError('Failed to post comment');
                }
            } catch (error) {
                console.error('Error posting comment:', error);
                showError('Network error. Please try again.');
            } finally {
                // Re-enable form
                submitBtn.innerHTML = originalHTML;
                submitBtn.disabled = false;
            }
        });
    });
}

/**
 * Follow/Unfollow team functionality
 */
function initializeFollowButton() {
    const followBtn = document.querySelector('.follow-btn');
    if (!followBtn) return;
    
    followBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        
        const teamSlug = getTeamSlugFromURL();
        if (!teamSlug) return;
        
        // Disable button during request
        const originalHTML = this.innerHTML;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processing...';
        this.disabled = true;
        
        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
            
            const response = await fetch(`/teams/${teamSlug}/follow/`, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    // Update button text and style
                    if (data.following) {
                        this.innerHTML = '<i class="fas fa-heart-broken me-1"></i> Unfollow';
                        this.classList.remove('btn-outline-primary');
                        this.classList.add('btn-outline-danger');
                    } else {
                        this.innerHTML = '<i class="fas fa-heart me-1"></i> Follow';
                        this.classList.remove('btn-outline-danger');
                        this.classList.add('btn-outline-primary');
                    }
                    
                    // Update follower count
                    updateFollowerCount(data.follower_count);
                    
                    // Show success message
                    showToast(data.message, 'success');
                }
            } else {
                showError('Failed to update follow status');
            }
        } catch (error) {
            console.error('Error toggling follow:', error);
            showError('Network error. Please try again.');
        } finally {
            this.disabled = false;
        }
    });
}

/**
 * Load more posts functionality
 */
function initializeLoadMore() {
    const loadMoreBtn = document.getElementById('load-more-posts');
    if (!loadMoreBtn) return;
    
    loadMoreBtn.addEventListener('click', async function() {
        const page = this.dataset.page;
        const teamSlug = getTeamSlugFromURL();
        
        if (!page || !teamSlug) return;
        
        const originalHTML = this.innerHTML;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';
        this.disabled = true;
        
        try {
            const response = await fetch(`/teams/${teamSlug}/posts/feed/?page=${page}`);
            
            if (response.ok) {
                const data = await response.json();
                
                // Add new posts to the feed
                const postsContainer = document.querySelector('.posts-feed');
                data.posts.forEach(post => {
                    const postHTML = createPostHTML(post);
                    postsContainer.insertAdjacentHTML('beforeend', postHTML);
                });
                
                // Update load more button
                if (data.has_next) {
                    this.dataset.page = parseInt(page) + 1;
                    this.innerHTML = originalHTML;
                    this.disabled = false;
                } else {
                    this.style.display = 'none';
                }
                
                // Reinitialize event listeners for new posts
                initializeLikeButtons();
                initializeCommentForms();
            }
        } catch (error) {
            console.error('Error loading more posts:', error);
            this.innerHTML = originalHTML;
            this.disabled = false;
            showError('Failed to load more posts');
        }
    });
}

/**
 * Media preview in post creation
 */
function initializeMediaPreview() {
    const mediaInput = document.querySelector('input[name="media"]');
    if (!mediaInput) return;
    
    mediaInput.addEventListener('change', function() {
        const file = this.files[0];
        if (!file) return;
        
        // Create preview container if it doesn't exist
        let previewContainer = document.querySelector('.media-preview');
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.className = 'media-preview mt-3';
            this.closest('.post-creation-card').querySelector('.card-body').appendChild(previewContainer);
        }
        
        // Clear previous preview
        previewContainer.innerHTML = '';
        
        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.className = 'img-fluid rounded';
            img.style.maxHeight = '200px';
            
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-sm btn-danger position-absolute top-0 end-0 m-2';
            removeBtn.innerHTML = '<i class="fas fa-times"></i>';
            removeBtn.onclick = () => {
                previewContainer.remove();
                mediaInput.value = '';
            };
            
            const wrapper = document.createElement('div');
            wrapper.className = 'position-relative d-inline-block';
            wrapper.appendChild(img);
            wrapper.appendChild(removeBtn);
            
            previewContainer.appendChild(wrapper);
        }
    });
}

/**
 * Enhanced post creation with character counter
 */
function initializePostCreation() {
    const contentTextarea = document.querySelector('.post-creation-card textarea[name="content"]');
    if (!contentTextarea) return;
    
    // Add character counter
    const maxLength = 5000;
    const counter = document.createElement('small');
    counter.className = 'text-muted position-absolute bottom-0 end-0 me-3 mb-2';
    counter.textContent = `0/${maxLength}`;
    
    const wrapper = contentTextarea.closest('.post-content-area');
    wrapper.style.position = 'relative';
    wrapper.appendChild(counter);
    
    contentTextarea.addEventListener('input', function() {
        const length = this.value.length;
        counter.textContent = `${length}/${maxLength}`;
        
        if (length > maxLength * 0.9) {
            counter.classList.add('text-warning');
        } else {
            counter.classList.remove('text-warning');
        }
        
        if (length > maxLength) {
            counter.classList.remove('text-warning');
            counter.classList.add('text-danger');
        } else {
            counter.classList.remove('text-danger');
        }
    });
}

/**
 * Utility Functions
 */

function getTeamSlugFromURL() {
    const pathParts = window.location.pathname.split('/');
    const teamsIndex = pathParts.indexOf('teams');
    return teamsIndex !== -1 && pathParts[teamsIndex + 1] ? pathParts[teamsIndex + 1] : null;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function animateHeartLike(heartIcon) {
    heartIcon.style.transform = 'scale(1.3)';
    heartIcon.style.transition = 'transform 0.2s ease';
    
    setTimeout(() => {
        heartIcon.style.transform = 'scale(1)';
    }, 200);
}

function addCommentToList(postId, commentData) {
    const commentsList = document.querySelector(`#comments-${postId} .comments-list`);
    if (!commentsList) return;
    
    const commentHTML = `
        <div class="comment-item mb-2">
            <div class="comment-content d-flex">
                <div class="user-avatar avatar-sm me-2">
                    <div class="avatar-placeholder rounded-circle d-flex align-items-center justify-content-center">
                        ${commentData.author_name.charAt(0).toUpperCase()}
                    </div>
                </div>
                <div class="comment-bubble bg-light rounded-3 px-3 py-2 flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="small">${commentData.author_name}</strong>
                        <small class="text-muted">Just now</small>
                    </div>
                    <p class="mb-0 small">${commentData.content}</p>
                </div>
            </div>
        </div>
    `;
    
    commentsList.insertAdjacentHTML('afterbegin', commentHTML);
}

function updateCommentCount(postId, increment) {
    const commentCount = document.querySelector(`[data-post-id="${postId}"] .comments-count`);
    if (commentCount) {
        const currentCount = parseInt(commentCount.textContent.match(/\d+/)[0]) + increment;
        commentCount.innerHTML = `<i class="fas fa-comment text-primary"></i> ${currentCount} ${currentCount === 1 ? 'comment' : 'comments'}`;
    }
}

function updateFollowerCount(count) {
    const followerElements = document.querySelectorAll('.follower-count, [data-follower-count]');
    followerElements.forEach(element => {
        if (element.textContent.includes('Followers')) {
            element.innerHTML = element.innerHTML.replace(/\d+/, count);
        }
    });
}

function showSuccessAnimation(element) {
    const originalHTML = element.innerHTML;
    element.innerHTML = '<i class="fas fa-check text-success"></i>';
    
    setTimeout(() => {
        element.innerHTML = originalHTML;
    }, 1000);
}

function showToast(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 3000);
}

function showError(message) {
    showToast(message, 'danger');
}

function createPostHTML(post) {
    // This would create HTML for a new post - simplified version
    return `
        <div class="card post-card mb-4 border-0 shadow-sm">
            <!-- Post content would be generated here -->
        </div>
    `;
}

// Comment toggle functionality
document.addEventListener('click', function(e) {
    if (e.target.matches('.comment-btn') || e.target.closest('.comment-btn')) {
        const postId = e.target.closest('.comment-btn').dataset.postId;
        const commentForm = document.querySelector(`#comments-${postId} .comment-form input`);
        if (commentForm) {
            commentForm.focus();
        }
    }
});

// View more comments functionality
document.addEventListener('click', function(e) {
    if (e.target.matches('.view-more-comments') || e.target.closest('.view-more-comments')) {
        e.preventDefault();
        const button = e.target.closest('.view-more-comments');
        const postId = button.dataset.postId;
        
        // This would load more comments via AJAX
        dcLog('Loading more comments for post:', postId);
    }
});
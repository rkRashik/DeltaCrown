// Follow/Unfollow System JavaScript
// Add to base template or profile-specific JS

async function followUser(username) {
    const button = event.target;
    button.disabled = true;
    button.textContent = 'Following...';
    
    try {
        const response = await fetch(`/actions/follow/${username}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            button.textContent = 'Following';
            button.onclick = () => unfollowUser(username);
            button.classList.remove('bg-gradient-to-r', 'from-indigo-600', 'to-purple-600');
            button.classList.add('bg-slate-700');
            
            // Update follower count
            updateFollowerCount(data.follower_count);
        } else {
            throw new Error(data.error || 'Failed to follow user');
        }
    } catch (error) {
        console.error('Follow error:', error);
        alert(error.message);
        button.textContent = '+ Follow';
    } finally {
        button.disabled = false;
    }
}

async function unfollowUser(username) {
    const button = event.target;
    button.disabled = true;
    button.textContent = 'Unfollowing...';
    
    try {
        const response = await fetch(`/actions/unfollow/${username}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            button.textContent = '+ Follow';
            button.onclick = () => followUser(username);
            button.classList.add('bg-gradient-to-r', 'from-indigo-600', 'to-purple-600');
            button.classList.remove('bg-slate-700');
            
            // Update follower count
            updateFollowerCount(data.follower_count);
        } else {
            throw new Error(data.error || 'Failed to unfollow user');
        }
    } catch (error) {
        console.error('Unfollow error:', error);
        alert(error.message);
        button.textContent = 'Following';
    } finally {
        button.disabled = false;
    }
}

function updateFollowerCount(count) {
    const followerElements = document.querySelectorAll('[data-follower-count]');
    followerElements.forEach(el => {
        el.textContent = count;
    });
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

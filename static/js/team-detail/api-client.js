/**
 * API Client for Team Detail Page
 * Handles all API communication with backend
 */

class TeamAPI {
  constructor(teamSlug, csrfToken) {
    this.teamSlug = teamSlug;
    this.csrfToken = csrfToken;
    this.baseUrl = `/teams/${teamSlug}`;
    this.logger = new Logger('TeamAPI');
  }

  /**
   * Helper method for making API requests
   */
  async request(url, options = {}) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfToken,
      },
    };

    const response = await fetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(error.error || error.message || 'Request failed');
    }

    return response.json();
  }

  /**
   * Get team roster
   */
  async getRoster() {
    try {
      return await this.request(`/teams/api/${this.teamSlug}/roster/`);
    } catch (error) {
      this.logger.error('Failed to fetch roster:', error);
      // Return empty roster on error
      return {
        active_players: [],
        inactive_players: [],
        statistics: null
      };
    }
  }

  /**
   * Get team roster with game IDs
   * Returns member data including game-specific IDs (only visible to team members)
   */
  async getRosterWithGameIds() {
    try {
      return await this.request(`/teams/api/${this.teamSlug}/roster-with-game-ids/`);
    } catch (error) {
      this.logger.error('Failed to fetch roster with game IDs:', error);
      // Return empty roster on error
      return {
        members: [],
        game_name: ''
      };
    }
  }

  /**
   * Get player details
   */
  async getPlayerDetails(playerId) {
    // Mock data - will be replaced with real API call
    return this.request(`${this.baseUrl}/roster/${playerId}/`);
  }

  /**
   * Search players (for adding to roster)
   */
  async searchPlayers(query) {
    // Mock data - will be replaced with real API call
    return [];
  }

  /**
   * Get team statistics
   */
  async getStatistics(params = {}) {
    // Return null for now - real API endpoint to be implemented
    // This will trigger the empty state in the statistics tab
    return null;
  }

  /**
   * Generate date labels for charts
   */
  generateDateLabels(days) {
    const labels = [];
    const today = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
    return labels;
  }

  /**
   * Generate mock win rate data
   */
  generateWinRateData(days) {
    const data = [];
    let baseRate = 60;
    for (let i = 0; i < days; i++) {
      baseRate += (Math.random() - 0.5) * 10;
      baseRate = Math.max(40, Math.min(80, baseRate));
      data.push(Math.round(baseRate));
    }
    return data;
  }

  /**
   * Get team tournaments
   */
  async getTournaments(params = {}) {
    try {
      return await this.request(`/teams/api/${this.teamSlug}/tournaments/`);
    } catch (error) {
      this.logger.error('Failed to fetch tournaments:', error);
      // Return empty tournaments on error
      return {
        active: [],
        upcomingMatches: [],
        history: []
      };
    }
  }

  /**
   * Get tournament details
   */
  async getTournamentDetails(tournamentId) {
    // Mock data - will be replaced with real API call
    return {
      id: tournamentId,
      name: 'Winter Championship 2025',
      organizer: 'ESports Pro League',
      status: 'active',
      start_date: '2025-01-01',
      end_date: '2025-01-31',
      prize_pool: 50000,
      team_count: 32,
      format: 'Double Elimination',
      banner_url: null,
      description: 'The biggest tournament of the winter season.',
      rules: '<p>Standard competition rules apply.</p>'
    };
  }

  /**
   * Get team posts
   */
  async getPosts(page = 1, filter = 'all', sort = 'recent') {
    try {
      const params = new URLSearchParams({ page, filter, sort });
      const response = await this.request(`/teams/api/${this.teamSlug}/posts/?${params}`);
      return response;
    } catch (error) {
      this.logger.error('Failed to fetch posts:', error);
      // Return empty posts on error
      return {
        posts: [],
        pagination: {
          page: 1,
          total_pages: 0,
          total_posts: 0,
          has_next: false,
          has_previous: false
        }
      };
    }
  }
  
  /**
   * Create new post
   */
  async createPost(content, postType = 'general') {
    try {
      return await this.request(`/teams/api/${this.teamSlug}/posts/create/`, {
        method: 'POST',
        body: JSON.stringify({ content, post_type: postType })
      });
    } catch (error) {
      this.logger.error('Failed to create post:', error);
      throw error;
    }
  }

  /**
   * Unlike a post
   */
  async unlikePost(postId) {
    return this.request(`${this.baseUrl}/posts/${postId}/unlike/`, {
      method: 'POST',
    });
  }

  /**
   * Get team discussions
   */
  async getDiscussions(params = {}) {
    try {
      const queryParams = new URLSearchParams(params).toString();
      const url = `/teams/api/${this.teamSlug}/discussions/${queryParams ? '?' + queryParams : ''}`;
      const response = await this.request(url);
      return response;
    } catch (error) {
      this.logger.error('Error fetching discussions:', error);
      return [];
    }
  }

  /**
   * Vote on discussion (upvote/downvote)
   */
  async voteDiscussion(discussionId, action) {
    try {
      const url = `/teams/api/${this.teamSlug}/discussions/${discussionId}/vote/`;
      return await this.request(url, {
        method: 'POST',
        body: JSON.stringify({ action })
      });
    } catch (error) {
      this.logger.error('Error voting on discussion:', error);
      throw error;
    }
  }

  /**
   * Create new discussion
   */
  async createDiscussion(data) {
    try {
      const url = `/teams/api/${this.teamSlug}/discussions/create/`;
      return await this.request(url, {
        method: 'POST',
        body: JSON.stringify(data)
      });
    } catch (error) {
      this.logger.error('Error creating discussion:', error);
      throw error;
    }
  }

  /**
   * Delete discussion
   */
  async deleteDiscussion(discussionId) {
    try {
      const url = `/teams/api/${this.teamSlug}/discussions/${discussionId}/delete/`;
      return await this.request(url, {
        method: 'DELETE'
      });
    } catch (error) {
      this.logger.error('Error deleting discussion:', error);
      throw error;
    }
  }

  /**
   * Get chat messages
   */
  async getChatMessages(beforeId = null) {
    try {
      const params = beforeId ? `?before_id=${beforeId}` : '';
      const url = `/teams/api/${this.teamSlug}/chat/messages/${params}`;
      const response = await this.request(url);
      return response;
    } catch (error) {
      this.logger.error('Error fetching chat messages:', error);
      return { messages: [], has_more: false };
    }
  }

  /**
   * Send chat message
   */
  async sendChatMessage(content, replyTo = null, attachment = null) {
    try {
      const url = `/teams/api/${this.teamSlug}/chat/messages/send/`;
      const data = { content };
      if (replyTo) data.reply_to = replyTo;
      if (attachment) data.attachment = attachment;
      
      return await this.request(url, {
        method: 'POST',
        body: JSON.stringify(data)
      });
    } catch (error) {
      this.logger.error('Error sending chat message:', error);
      throw error;
    }
  }

  /**
   * Edit chat message
   */
  async editChatMessage(messageId, content) {
    try {
      const url = `/teams/api/${this.teamSlug}/chat/messages/${messageId}/edit/`;
      return await this.request(url, {
        method: 'PATCH',
        body: JSON.stringify({ content })
      });
    } catch (error) {
      this.logger.error('Error editing chat message:', error);
      throw error;
    }
  }

  /**
   * Delete chat message
   */
  async deleteChatMessage(messageId) {
    try {
      const url = `/teams/api/${this.teamSlug}/chat/messages/${messageId}/delete/`;
      return await this.request(url, {
        method: 'DELETE'
      });
    } catch (error) {
      this.logger.error('Error deleting chat message:', error);
      throw error;
    }
  }

  /**
   * Add reaction to chat message
   */
  async addMessageReaction(messageId, emoji) {
    try {
      const url = `/teams/api/${this.teamSlug}/chat/messages/${messageId}/react/`;
      return await this.request(url, {
        method: 'POST',
        body: JSON.stringify({ emoji })
      });
    } catch (error) {
      this.logger.error('Error adding reaction:', error);
      throw error;
    }
  }

  /**
   * Remove reaction from chat message
   */
  async removeMessageReaction(messageId, emoji) {
    try {
      const url = `/teams/api/${this.teamSlug}/chat/messages/${messageId}/unreact/`;
      return await this.request(url, {
        method: 'DELETE',
        body: JSON.stringify({ emoji })
      });
    } catch (error) {
      this.logger.error('Error removing reaction:', error);
      throw error;
    }
  }

  /**
   * Get team sponsors
   */
  async getSponsors() {
    try {
      const response = await this.request(`/teams/api/${this.teamSlug}/sponsors/`);
      return response;
    } catch (error) {
      this.logger.error('Failed to fetch sponsors:', error);
      // Return empty array on error
      return [];
    }
  }

  /**
   * Add new sponsor
   */
  async addSponsor(data) {
    return this.request(`/teams/api/${this.teamSlug}/sponsors/add/`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  /**
   * Update sponsor
   */
  async updateSponsor(sponsorId, data) {
    return this.request(`/teams/api/${this.teamSlug}/sponsors/${sponsorId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  /**
   * Delete sponsor
   */
  async deleteSponsor(sponsorId) {
    return this.request(`/teams/api/${this.teamSlug}/sponsors/${sponsorId}/delete/`, {
      method: 'DELETE'
    });
  }

  /**
   * Get single post details
   */
  async getPost(postId) {
    // Mock data - will be replaced with real API call
    return this.request(`${this.baseUrl}/posts/${postId}/`);
  }

  /**
   * Like a post
   */
  async likePost(postId) {
    return this.request(`${this.baseUrl}/posts/${postId}/like/`, {
      method: 'POST',
    });
  }

  /**
   * Follow team
   */
  async followTeam() {
    return this.request(`${this.baseUrl}/follow/`, {
      method: 'POST',
    });
  }

  /**
   * Unfollow team
   */
  async unfollowTeam() {
    return this.request(`${this.baseUrl}/unfollow/`, {
      method: 'POST',
    });
  }



  /**
   * Get team overview data
   */
  async getOverview() {
    // For now, return basic structure - will be implemented in Phase 2
    return {
      description: 'Team description will be loaded here',
      recent_matches: [],
      latest_posts: [],
      achievements: []
    };
  }
}

// Initialize API client when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const pageData = JSON.parse(document.getElementById('page-data').textContent);
  window.teamAPI = new TeamAPI(pageData.team.slug, pageData.csrf_token);
  const logger = new Logger('TeamAPI');
  logger.log('Initialized for team:', pageData.team.slug);
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TeamAPI;
}

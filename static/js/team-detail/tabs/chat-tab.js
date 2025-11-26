/**
 * Chat Tab Component
 * Real-time team chat with WebSocket support
 */

class ChatTab {
  constructor(api) {
    this.api = api;
    this.container = document.getElementById('chat-content');
    this.ws = null;
    this.currentChannel = 'team'; // team, captain, announcements
    this.messages = [];
    this.typingUsers = new Set();
    this.typingTimeout = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.isConnected = false;
  }

  async render() {
    if (!this.container) {
      console.error('Chat container not found');
      return;
    }

    // Show loading state
    this.container.innerHTML = this.getLoadingState();

    try {
      // Load initial messages
      this.messages = await this.api.getChatMessages(this.currentChannel);

      // Render the chat UI
      this.container.innerHTML = this.getChatContent();

      // Initialize WebSocket connection
      this.initWebSocket();

      // Attach event listeners
      this.attachEventListeners();

      // Scroll to bottom
      this.scrollToBottom();
    } catch (error) {
      console.error('Error loading chat:', error);
      this.container.innerHTML = this.getErrorState();
    }
  }

  getChatContent() {
    const permissions = this.api.permissions;
    
    return `
      <div class="chat-layout">
        <!-- Chat Header -->
        <div class="chat-header">
          <div class="chat-header-left">
            <h2>
              <i class="fas fa-message"></i>
              Team Chat
            </h2>
            <span class="connection-status ${this.isConnected ? 'connected' : 'disconnected'}">
              <i class="fas fa-circle"></i>
              ${this.isConnected ? 'Connected' : 'Connecting...'}
            </span>
          </div>
          
          <div class="chat-channels">
            <button class="channel-btn ${this.currentChannel === 'team' ? 'active' : ''}" 
                    data-channel="team">
              <i class="fas fa-users"></i>
              Team
            </button>
            ${permissions.is_captain ? `
              <button class="channel-btn ${this.currentChannel === 'captain' ? 'active' : ''}" 
                      data-channel="captain">
                <i class="fas fa-crown"></i>
                Captain
              </button>
            ` : ''}
            <button class="channel-btn ${this.currentChannel === 'announcements' ? 'active' : ''}" 
                    data-channel="announcements">
              <i class="fas fa-bullhorn"></i>
              Announcements
            </button>
          </div>

          <div class="chat-actions">
            <button class="icon-btn" data-action="search" title="Search messages">
              <i class="fas fa-search"></i>
            </button>
            <button class="icon-btn" data-action="members" title="View members">
              <i class="fas fa-users"></i>
            </button>
            <button class="icon-btn" data-action="settings" title="Chat settings">
              <i class="fas fa-gear"></i>
            </button>
          </div>
        </div>

        <!-- Messages Container -->
        <div class="chat-messages" id="chat-messages">
          ${this.renderMessages()}
          
          <!-- Typing Indicator -->
          <div class="typing-indicator ${this.typingUsers.size > 0 ? 'show' : ''}" id="typing-indicator">
            ${this.renderTypingIndicator()}
          </div>
        </div>

        <!-- Message Input -->
        <div class="chat-input-container">
          <div class="chat-input-wrapper">
            <button class="icon-btn" data-action="emoji" title="Add emoji">
              <i class="fas fa-smile"></i>
            </button>
            
            <button class="icon-btn" data-action="attach" title="Attach file">
              <i class="fas fa-paperclip"></i>
            </button>
            
            <textarea 
              id="chat-message-input" 
              class="chat-input" 
              placeholder="Type a message..."
              rows="1"
              maxlength="2000"></textarea>
            
            <button class="btn-send" id="send-message-btn" title="Send message">
              <i class="fas fa-paper-plane"></i>
            </button>
          </div>
          
          <div class="chat-input-info">
            <span class="char-count">
              <span id="char-count">0</span>/2000
            </span>
          </div>
        </div>
      </div>
    `;
  }

  renderMessages() {
    if (this.messages.length === 0) {
      return this.getEmptyMessagesState();
    }

    let html = '';
    let lastDate = null;
    let lastAuthorId = null;

    this.messages.forEach((message, index) => {
      const messageDate = new Date(message.created_at).toDateString();
      
      // Add date divider if date changed
      if (messageDate !== lastDate) {
        html += this.renderDateDivider(message.created_at);
        lastDate = messageDate;
        lastAuthorId = null;
      }

      // Check if we should group this message with the previous one
      const isGrouped = lastAuthorId === message.author.id && 
                       index > 0 && 
                       (new Date(message.created_at) - new Date(this.messages[index - 1].created_at)) < 300000; // 5 minutes

      html += this.renderMessage(message, isGrouped);
      lastAuthorId = message.author.id;
    });

    return html;
  }

  renderDateDivider(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    let label;
    if (date.toDateString() === today.toDateString()) {
      label = 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      label = 'Yesterday';
    } else {
      label = date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    }

    return `
      <div class="message-date-divider">
        <span>${label}</span>
      </div>
    `;
  }

  renderMessage(message, isGrouped = false) {
    const time = new Date(message.created_at).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    const isOwnMessage = message.is_own;
    const isSystem = message.type === 'system';
    const isAnnouncement = message.type === 'announcement';

    if (isSystem) {
      return `
        <div class="message message-system">
          <i class="fas fa-info-circle"></i>
          <span>${this.escapeHtml(message.content)}</span>
        </div>
      `;
    }

    return `
      <div class="message ${isOwnMessage ? 'message-own' : 'message-other'} ${isGrouped ? 'message-grouped' : ''} ${isAnnouncement ? 'message-announcement' : ''}" 
           data-message-id="${message.id}">
        ${!isGrouped ? `
          <img src="${message.author.avatar_url}" 
               alt="${message.author.display_name}" 
               class="message-avatar">
        ` : '<div class="message-avatar-placeholder"></div>'}
        
        <div class="message-content-wrapper">
          ${!isGrouped ? `
            <div class="message-header">
              <span class="message-author">${this.escapeHtml(message.author.display_name)}</span>
              ${message.author.role ? `<span class="message-role">${message.author.role}</span>` : ''}
              <span class="message-time">${time}</span>
            </div>
          ` : ''}
          
          <div class="message-content">
            ${this.formatMessageContent(message.content)}
            
            ${message.attachments && message.attachments.length > 0 ? `
              <div class="message-attachments">
                ${message.attachments.map(att => this.renderAttachment(att)).join('')}
              </div>
            ` : ''}
            
            ${message.reactions && Object.keys(message.reactions).length > 0 ? `
              <div class="message-reactions">
                ${this.renderReactions(message.reactions, message.id)}
              </div>
            ` : ''}
          </div>
          
          <div class="message-actions">
            <button class="message-action-btn" data-action="react" data-message-id="${message.id}" title="Add reaction">
              <i class="fas fa-smile"></i>
            </button>
            <button class="message-action-btn" data-action="reply" data-message-id="${message.id}" title="Reply">
              <i class="fas fa-reply"></i>
            </button>
            ${isOwnMessage ? `
              <button class="message-action-btn" data-action="edit" data-message-id="${message.id}" title="Edit">
                <i class="fas fa-edit"></i>
              </button>
              <button class="message-action-btn" data-action="delete" data-message-id="${message.id}" title="Delete">
                <i class="fas fa-trash"></i>
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }

  formatMessageContent(content) {
    // Simple formatting: links, mentions, emojis
    let formatted = this.escapeHtml(content);
    
    // Make URLs clickable
    formatted = formatted.replace(
      /(https?:\/\/[^\s]+)/g, 
      '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    
    // Highlight mentions
    formatted = formatted.replace(
      /@(\w+)/g, 
      '<span class="mention">@$1</span>'
    );
    
    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
  }

  renderAttachment(attachment) {
    if (attachment.type === 'image') {
      return `
        <a href="${attachment.url}" target="_blank" class="attachment attachment-image">
          <img src="${attachment.url}" alt="${attachment.name}" loading="lazy">
        </a>
      `;
    } else {
      return `
        <a href="${attachment.url}" target="_blank" class="attachment attachment-file">
          <i class="fas fa-file"></i>
          <span>${this.escapeHtml(attachment.name)}</span>
          <span class="attachment-size">${this.formatFileSize(attachment.size)}</span>
        </a>
      `;
    }
  }

  renderReactions(reactions, messageId) {
    return Object.entries(reactions).map(([emoji, users]) => `
      <button class="reaction ${users.includes('current_user') ? 'reaction-active' : ''}" 
              data-emoji="${emoji}" 
              data-message-id="${messageId}">
        <span class="reaction-emoji">${emoji}</span>
        <span class="reaction-count">${users.length}</span>
      </button>
    `).join('');
  }

  renderTypingIndicator() {
    if (this.typingUsers.size === 0) return '';
    
    const users = Array.from(this.typingUsers);
    let text;
    
    if (users.length === 1) {
      text = `${users[0]} is typing`;
    } else if (users.length === 2) {
      text = `${users[0]} and ${users[1]} are typing`;
    } else {
      text = `${users.length} people are typing`;
    }
    
    return `
      <div class="typing-dots">
        <span>${text}</span>
        <span class="dots">
          <span>.</span><span>.</span><span>.</span>
        </span>
      </div>
    `;
  }

  initWebSocket() {
    // In production, this would connect to a real WebSocket server
    // For now, we'll simulate WebSocket behavior with mock events
    
    // Simulate connection
    setTimeout(() => {
      this.isConnected = true;
      this.updateConnectionStatus();
      dcLog('Chat WebSocket connected (simulated)');
    }, 1000);

    // Simulate incoming messages every 30 seconds (for demo)
    setInterval(() => {
      if (Math.random() > 0.7) { // 30% chance
        this.simulateIncomingMessage();
      }
    }, 30000);
  }

  simulateIncomingMessage() {
    const mockMessage = {
      id: Date.now(),
      author: {
        id: 999,
        display_name: 'Team Member',
        avatar_url: '/static/img/default-avatar.png',
        role: 'Member'
      },
      content: 'Hey team! Just checking in.',
      created_at: new Date().toISOString(),
      type: 'message',
      is_own: false,
      attachments: [],
      reactions: {}
    };

    this.addMessage(mockMessage);
  }

  updateConnectionStatus() {
    const statusEl = this.container.querySelector('.connection-status');
    if (statusEl) {
      statusEl.className = `connection-status ${this.isConnected ? 'connected' : 'disconnected'}`;
      statusEl.innerHTML = `
        <i class="fas fa-circle"></i>
        ${this.isConnected ? 'Connected' : 'Connecting...'}
      `;
    }
  }

  attachEventListeners() {
    // Channel switching
    this.container.querySelectorAll('[data-channel]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.switchChannel(btn.dataset.channel);
      });
    });

    // Message input
    const input = this.container.querySelector('#chat-message-input');
    const sendBtn = this.container.querySelector('#send-message-btn');
    const charCount = this.container.querySelector('#char-count');

    if (input) {
      // Auto-resize textarea
      input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 150) + 'px';
        
        // Update character count
        if (charCount) {
          charCount.textContent = input.value.length;
        }

        // Send typing indicator
        this.sendTypingIndicator();
      });

      // Send on Enter (Shift+Enter for new line)
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }

    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.sendMessage());
    }

    // Chat actions
    this.container.querySelectorAll('[data-action="emoji"]').forEach(btn => {
      btn.addEventListener('click', () => this.showEmojiPicker());
    });

    this.container.querySelectorAll('[data-action="attach"]').forEach(btn => {
      btn.addEventListener('click', () => this.showFileUpload());
    });

    // Message actions (use event delegation for dynamic content)
    const messagesContainer = this.container.querySelector('#chat-messages');
    if (messagesContainer) {
      messagesContainer.addEventListener('click', (e) => {
        const actionBtn = e.target.closest('.message-action-btn');
        if (actionBtn) {
          const action = actionBtn.dataset.action;
          const messageId = actionBtn.dataset.messageId;
          this.handleMessageAction(action, messageId);
        }

        const reaction = e.target.closest('.reaction');
        if (reaction) {
          const emoji = reaction.dataset.emoji;
          const messageId = reaction.dataset.messageId;
          this.toggleReaction(messageId, emoji);
        }
      });
    }
  }

  async switchChannel(channel) {
    this.currentChannel = channel;
    
    // Show loading
    const messagesContainer = this.container.querySelector('#chat-messages');
    if (messagesContainer) {
      messagesContainer.innerHTML = '<div class="loading-messages"><i class="fas fa-spinner fa-spin"></i></div>';
    }

    // Load messages for new channel
    this.messages = await this.api.getChatMessages(channel);
    
    // Re-render
    await this.render();
  }

  async sendMessage() {
    const input = this.container.querySelector('#chat-message-input');
    if (!input) return;

    const content = input.value.trim();
    if (!content) return;

    // Create optimistic message
    const message = {
      id: Date.now(),
      author: {
        id: 'current_user',
        display_name: 'You',
        avatar_url: '/static/img/default-avatar.png',
        role: this.api.permissions.is_captain ? 'Captain' : 'Member'
      },
      content,
      created_at: new Date().toISOString(),
      type: 'message',
      is_own: true,
      attachments: [],
      reactions: {}
    };

    // Add to UI immediately
    this.addMessage(message);

    // Clear input
    input.value = '';
    input.style.height = 'auto';
    this.container.querySelector('#char-count').textContent = '0';

    // Send to server (would be via WebSocket in production)
    try {
      await this.api.sendChatMessage(this.currentChannel, content);
    } catch (error) {
      console.error('Error sending message:', error);
      // Could show error indicator on message
    }
  }

  addMessage(message) {
    this.messages.push(message);
    
    // Re-render messages
    const messagesContainer = this.container.querySelector('#chat-messages');
    if (messagesContainer) {
      const typingIndicator = messagesContainer.querySelector('.typing-indicator');
      const messagesHtml = this.renderMessages();
      messagesContainer.innerHTML = messagesHtml;
      
      // Re-add typing indicator
      if (typingIndicator) {
        messagesContainer.appendChild(typingIndicator);
      }
      
      this.scrollToBottom();
    }
  }

  sendTypingIndicator() {
    // Debounce typing indicator
    clearTimeout(this.typingTimeout);
    
    // Send typing event (would be via WebSocket)
    // In production: this.ws.send(JSON.stringify({ type: 'typing' }));
    
    this.typingTimeout = setTimeout(() => {
      // Send stopped typing event
      // In production: this.ws.send(JSON.stringify({ type: 'typing_stopped' }));
    }, 3000);
  }

  handleMessageAction(action, messageId) {
    switch (action) {
      case 'react':
        this.showReactionPicker(messageId);
        break;
      case 'reply':
        this.replyToMessage(messageId);
        break;
      case 'edit':
        this.editMessage(messageId);
        break;
      case 'delete':
        this.deleteMessage(messageId);
        break;
    }
  }

  showEmojiPicker() {
    // Simple emoji picker (could be enhanced with a library)
    const emojis = ['😀', '😂', '❤️', '👍', '🎉', '🔥', '👏', '✨'];
    // For now, just log - full implementation would show a picker modal
    dcLog('Emoji picker:', emojis);
  }

  showFileUpload() {
    // Create file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*,application/pdf,.doc,.docx';
    input.onchange = (e) => this.handleFileUpload(e.target.files);
    input.click();
  }

  async handleFileUpload(files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    dcLog('Uploading file:', file.name);
    
    // In production, upload file and add as attachment
    // For now, just show a placeholder message
    const message = {
      id: Date.now(),
      author: {
        id: 'current_user',
        display_name: 'You',
        avatar_url: '/static/img/default-avatar.png',
        role: 'Member'
      },
      content: `Uploaded: ${file.name}`,
      created_at: new Date().toISOString(),
      type: 'message',
      is_own: true,
      attachments: [{
        type: file.type.startsWith('image/') ? 'image' : 'file',
        url: URL.createObjectURL(file),
        name: file.name,
        size: file.size
      }],
      reactions: {}
    };
    
    this.addMessage(message);
  }

  showReactionPicker(messageId) {
    const emojis = ['👍', '❤️', '😂', '🎉', '🔥', '👏'];
    // For now, just add the first emoji
    this.toggleReaction(messageId, emojis[0]);
  }

  toggleReaction(messageId, emoji) {
    const message = this.messages.find(m => m.id == messageId);
    if (!message) return;

    if (!message.reactions) {
      message.reactions = {};
    }

    if (!message.reactions[emoji]) {
      message.reactions[emoji] = [];
    }

    const userIndex = message.reactions[emoji].indexOf('current_user');
    if (userIndex > -1) {
      message.reactions[emoji].splice(userIndex, 1);
      if (message.reactions[emoji].length === 0) {
        delete message.reactions[emoji];
      }
    } else {
      message.reactions[emoji].push('current_user');
    }

    // Re-render the message
    const messageEl = this.container.querySelector(`[data-message-id="${messageId}"]`);
    if (messageEl) {
      const temp = document.createElement('div');
      temp.innerHTML = this.renderMessage(message);
      messageEl.replaceWith(temp.firstElementChild);
    }
  }

  replyToMessage(messageId) {
    const input = this.container.querySelector('#chat-message-input');
    if (input) {
      const message = this.messages.find(m => m.id == messageId);
      if (message) {
        input.value = `@${message.author.display_name} `;
        input.focus();
      }
    }
  }

  editMessage(messageId) {
    // TODO: Implement edit functionality
    dcLog('Edit message:', messageId);
  }

  async deleteMessage(messageId) {
    if (!confirm('Are you sure you want to delete this message?')) return;
    
    try {
      await this.api.deleteChatMessage(messageId);
      
      // Remove from UI
      this.messages = this.messages.filter(m => m.id != messageId);
      
      // Re-render
      const messagesContainer = this.container.querySelector('#chat-messages');
      if (messagesContainer) {
        messagesContainer.innerHTML = this.renderMessages();
      }
    } catch (error) {
      console.error('Error deleting message:', error);
    }
  }

  scrollToBottom(smooth = true) {
    const messagesContainer = this.container.querySelector('#chat-messages');
    if (messagesContainer) {
      messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      });
    }
  }

  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  getLoadingState() {
    return SkeletonLoaders.list(8, SkeletonLoaders.chatMessage());
  }

  getEmptyMessagesState() {
    return `
      <div class="empty-messages-state">
        <i class="fas fa-message"></i>
        <h3>No messages yet</h3>
        <p>Be the first to send a message!</p>
      </div>
    `;
  }

  getErrorState() {
    return `
      <div class="error-state">
        <i class="fas fa-exclamation-circle"></i>
        <h3>Failed to load chat</h3>
        <p>Please try again later.</p>
        <button class="btn btn-primary" onclick="location.reload()">
          <i class="fas fa-refresh"></i>
          Retry
        </button>
      </div>
    `;
  }

  destroy() {
    // Cleanup WebSocket connection
    if (this.ws) {
      this.ws.close();
    }
    clearTimeout(this.typingTimeout);
  }
}

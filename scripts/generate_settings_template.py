#!/usr/bin/env python3
"""
Script to generate the new modular settings.html template for Phase 6 Part C
Replaces the 2000-line monolithic template with a clean 6-section design
"""

SETTINGS_TEMPLATE = '''{% extends "base.html" %}
{% load static %}

{% block title %}Settings - DeltaCrown{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/settings_v2.css' %}">
{% endblock %}

{% block content %}
<div class="settings-container" x-data="settingsApp()">
    <!-- Page Header -->
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-white mb-2">Settings</h1>
        <p class="text-slate-400">Manage your account and platform preferences</p>
    </div>

    <div class="settings-grid">
        <!-- Navigation Sidebar -->
        <nav class="settings-nav">
            <div class="nav-header">⚙️ Menu</div>
            
            <div class="nav-item" :class="{'active': activeSection === 'profile'}" @click="switchSection('profile')">
                <span class="nav-icon">👤</span><span>Profile</span>
            </div>
            <div class="nav-item" :class="{'active': activeSection === 'privacy'}" @click="switchSection('privacy')">
                <span class="nav-icon">🔒</span><span>Privacy</span>
            </div>
            <div class="nav-item" :class="{'active': activeSection === 'notifications'}" @click="switchSection('notifications')">
                <span class="nav-icon">🔔</span><span>Notifications</span>
            </div>
            <div class="nav-item" :class="{'active': activeSection === 'platform'}" @click="switchSection('platform')">
                <span class="nav-icon">🌐</span><span>Platform</span>
            </div>
            <div class="nav-item" :class="{'active': activeSection === 'wallet'}" @click="switchSection('wallet')">
                <span class="nav-icon">💰</span><span>Wallet</span>
            </div>
            <div class="nav-item" :class="{'active': activeSection === 'account'}" @click="switchSection('account')">
                <span class="nav-icon">🛡️</span><span>Account</span>
            </div>
        </nav>

        <!-- Content Area -->
        <div class="settings-content">
            <!-- Alerts -->
            <div x-show="alert.show" x-transition class="alert" :class="'alert-' + alert.type">
                <span x-text="alert.icon"></span>
                <span x-text="alert.message"></span>
            </div>

            <!-- PROFILE SECTION -->
            <section x-show="activeSection === 'profile'" x-transition class="content-section">
                <div class="section-header">
                    <span class="section-icon">👤</span>
                    <div>
                        <h2 class="section-title">Profile</h2>
                        <p class="section-description">Manage your public identity</p>
                    </div>
                </div>

                <form @submit.prevent="saveProfile">
                    <div class="form-group">
                        <label class="form-label">Display Name</label>
                        <input type="text" class="form-input" x-model="profile.display_name" required>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Bio</label>
                        <textarea class="form-textarea" x-model="profile.bio" maxlength="500"></textarea>
                        <span class="form-hint">Max 500 characters</span>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Country</label>
                        <select class="form-select" x-model="profile.country">
                            <option value="">Select Country</option>
                            <option value="BD">Bangladesh</option>
                            <option value="IN">India</option>
                            <option value="PK">Pakistan</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Pronouns</label>
                        <input type="text" class="form-input" x-model="profile.pronouns" placeholder="e.g., he/him, she/her">
                    </div>

                    <button type="submit" class="btn btn-primary" :disabled="loading">
                        <span x-show="!loading">💾 Save Changes</span>
                        <span x-show="loading">Saving...</span>
                    </button>
                </form>
            </section>

            <!-- PRIVACY SECTION -->
            <section x-show="activeSection === 'privacy'" x-transition class="content-section">
                <div class="section-header">
                    <span class="section-icon">🔒</span>
                    <div>
                        <h2 class="section-title">Privacy</h2>
                        <p class="section-description">Control who can see your information</p>
                    </div>
                </div>

                <div class="info-card">
                    <div class="card-header">🔒 Privacy Settings</div>
                    <div class="card-content">
                        <p class="mb-4">Manage detailed privacy controls for your profile, game data, and interactions.</p>
                        <a href="{% url 'user_profile:profile_privacy_v2' %}" class="btn btn-primary">
                            Manage Privacy Settings
                        </a>
                    </div>
                </div>
            </section>

            <!-- NOTIFICATIONS SECTION -->
            <section x-show="activeSection === 'notifications'" x-transition class="content-section">
                <div class="section-header">
                    <span class="section-icon">🔔</span>
                    <div>
                        <h2 class="section-title">Notifications</h2>
                        <p class="section-description">Choose how you want to be notified</p>
                    </div>
                </div>

                <form @submit.prevent="saveNotifications">
                    <h3 class="text-lg font-bold text-white mb-3">Email Notifications</h3>
                    
                    <template x-for="(pref, key) in notifications.email" :key="key">
                        <div class="toggle-group">
                            <div class="toggle-label">
                                <div class="toggle-title" x-text="pref.title"></div>
                                <div class="toggle-description" x-text="pref.description"></div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" x-model="pref.value" class="toggle-input">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </template>

                    <h3 class="text-lg font-bold text-white mb-3 mt-6">Platform Notifications</h3>
                    
                    <template x-for="(pref, key) in notifications.platform" :key="key">
                        <div class="toggle-group">
                            <div class="toggle-label">
                                <div class="toggle-title" x-text="pref.title"></div>
                                <div class="toggle-description" x-text="pref.description"></div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" x-model="pref.value" class="toggle-input">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </template>

                    <button type="submit" class="btn btn-primary mt-6" :disabled="loading">
                        <span x-show="!loading">💾 Save Preferences</span>
                        <span x-show="loading">Saving...</span>
                    </button>
                </form>
            </section>

            <!-- PLATFORM SECTION -->
            <section x-show="activeSection === 'platform'" x-transition class="content-section">
                <div class="section-header">
                    <span class="section-icon">🌐</span>
                    <div>
                        <h2 class="section-title">Platform Preferences</h2>
                        <p class="section-description">Customize your DeltaCrown experience</p>
                    </div>
                </div>

                <form @submit.prevent="savePlatform">
                    <div class="form-group">
                        <label class="form-label">Language</label>
                        <select class="form-select" x-model="platform.preferred_language">
                            <option value="en">English</option>
                            <option value="bn" disabled>Bengali (Coming Soon)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Timezone</label>
                        <select class="form-select" x-model="platform.timezone_pref">
                            <option value="Asia/Dhaka">Asia/Dhaka (GMT+6)</option>
                            <option value="Asia/Kolkata">Asia/Kolkata (GMT+5:30)</option>
                            <option value="UTC">UTC</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Time Format</label>
                        <select class="form-select" x-model="platform.time_format">
                            <option value="12h">12-hour (3:00 PM)</option>
                            <option value="24h">24-hour (15:00)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Theme</label>
                        <select class="form-select" x-model="platform.theme_preference">
                            <option value="dark">Dark</option>
                            <option value="light">Light</option>
                            <option value="system">System</option>
                        </select>
                    </div>

                    <button type="submit" class="btn btn-primary" :disabled="loading">
                        <span x-show="!loading">💾 Save Preferences</span>
                        <span x-show="loading">Saving...</span>
                    </button>
                </form>
            </section>

            <!-- WALLET SECTION -->
            <section x-show="activeSection === 'wallet'" x-transition class="content-section">
                <div class="section-header">
                    <span class="section-icon">💰</span>
                    <div>
                        <h2 class="section-title">Wallet & Withdrawals</h2>
                        <p class="section-description">Manage your DeltaCoins</p>
                    </div>
                </div>

                <div class="balance-display">
                    <div class="balance-amount">{{ user_profile.deltacoin_balance|default:0 }}</div>
                    <div class="balance-label">DeltaCoins Available</div>
                </div>

                <form @submit.prevent="saveWallet">
                    <h3 class="text-lg font-bold text-white mb-3">Withdrawal Methods</h3>
                    
                    <template x-for="method in ['bkash', 'nagad', 'rocket']" :key="method">
                        <div class="form-group">
                            <div class="toggle-group">
                                <div class="toggle-label">
                                    <div class="toggle-title" x-text="method.toUpperCase()"></div>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" x-model="wallet[method + '_enabled']" class="toggle-input">
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                            <input type="text" class="form-input mt-2" x-model="wallet[method + '_account']" 
                                   placeholder="01XXXXXXXXX" pattern="01[3-9]\\d{8}"
                                   x-show="wallet[method + '_enabled']">
                        </div>
                    </template>

                    <button type="submit" class="btn btn-primary mt-6" :disabled="loading">
                        <span x-show="!loading">💾 Save Settings</span>
                        <span x-show="loading">Saving...</span>
                    </button>
                </form>
            </section>

            <!-- ACCOUNT SECTION -->
            <section x-show="activeSection === 'account'" x-transition class="content-section">
                <div class="section-header">
                    <span class="section-icon">🛡️</span>
                    <div>
                        <h2 class="section-title">Account & Security</h2>
                        <p class="section-description">Manage your account security</p>
                    </div>
                </div>

                <div class="info-card mb-6">
                    <div class="card-header">🔐 Password</div>
                    <div class="card-content">
                        <a href="{% url 'password_change' %}" class="btn btn-secondary">Change Password</a>
                    </div>
                </div>

                <div class="info-card" style="border-color: var(--accent-danger);">
                    <div class="card-header" style="color: var(--accent-danger);">⚠️ Danger Zone</div>
                    <div class="card-content">
                        <button type="button" class="btn btn-danger" @click="deleteAccount">
                            🗑️ Delete Account
                        </button>
                    </div>
                </div>
            </section>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
<script>
function settingsApp() {
    return {
        activeSection: window.location.hash.substring(1) || 'profile',
        loading: false,
        alert: { show: false, type: '', message: '', icon: '' },
        profile: { display_name: '{{ user_profile.display_name }}', bio: '{{ user_profile.bio }}', country: '{{ user_profile.country }}', pronouns: '{{ user_profile.pronouns }}' },
        notifications: {
            email: {
                tournament_reminders: { title: 'Tournament Reminders', description: 'Upcoming tournaments', value: true },
                match_results: { title: 'Match Results', description: 'When results are published', value: true },
                team_invites: { title: 'Team Invites', description: 'Team invitation notifications', value: true },
                achievements: { title: 'Achievements', description: 'Achievement unlocks', value: false },
                platform_updates: { title: 'Platform Updates', description: 'New features and news', value: true }
            },
            platform: {
                tournament_start: { title: 'Tournament Start', description: 'When tournaments begin', value: true },
                team_messages: { title: 'Team Messages', description: 'New team messages', value: true },
                follows: { title: 'New Followers', description: 'When someone follows you', value: true },
                achievements: { title: 'Achievement Popups', description: 'Unlock notifications', value: true }
            }
        },
        platform: { preferred_language: '{{ user_profile.preferred_language }}', timezone_pref: '{{ user_profile.timezone_pref }}', time_format: '{{ user_profile.time_format }}', theme_preference: '{{ user_profile.theme_preference }}' },
        wallet: { bkash_enabled: false, bkash_account: '', nagad_enabled: false, nagad_account: '', rocket_enabled: false, rocket_account: '', auto_withdrawal_threshold: 0, auto_convert_to_usd: false },

        init() {
            this.loadNotifications();
            this.loadWallet();
        },

        switchSection(section) {
            this.activeSection = section;
            window.location.hash = section;
            window.scrollTo({top: 0, behavior: 'smooth'});
        },

        async loadNotifications() {
            try {
                const res = await fetch('{% url "user_profile:get_notification_preferences" %}');
                const data = await res.json();
                if (data.success) {
                    Object.keys(this.notifications.email).forEach(key => {
                        this.notifications.email[key].value = data.preferences['email_' + key] ?? true;
                    });
                    Object.keys(this.notifications.platform).forEach(key => {
                        this.notifications.platform[key].value = data.preferences['notify_' + key] ?? true;
                    });
                }
            } catch (e) {}
        },

        async loadWallet() {
            try {
                const res = await fetch('{% url "user_profile:get_wallet_settings" %}');
                const data = await res.json();
                if (data.success) Object.assign(this.wallet, data.settings);
            } catch (e) {}
        },

        async saveProfile() {
            this.loading = true;
            try {
                const formData = new FormData();
                Object.keys(this.profile).forEach(k => formData.append(k, this.profile[k]));
                formData.append('csrfmiddlewaretoken', '{{ csrf_token }}');
                
                const res = await fetch('{% url "user_profile:update_basic_info" %}', { method: 'POST', body: formData });
                const data = await res.json();
                this.showAlert(data.success ? 'success' : 'error', data.success ? 'Profile updated!' : data.error);
            } catch (e) {
                this.showAlert('error', 'Network error');
            }
            this.loading = false;
        },

        async saveNotifications() {
            this.loading = true;
            try {
                const payload = {};
                Object.keys(this.notifications.email).forEach(k => payload['email_' + k] = this.notifications.email[k].value);
                Object.keys(this.notifications.platform).forEach(k => payload['notify_' + k] = this.notifications.platform[k].value);
                
                const res = await fetch('{% url "user_profile:update_notification_preferences" %}', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                this.showAlert(data.success ? 'success' : 'error', data.success ? 'Preferences saved!' : data.error);
            } catch (e) {
                this.showAlert('error', 'Network error');
            }
            this.loading = false;
        },

        async savePlatform() {
            this.loading = true;
            try {
                const res = await fetch('{% url "user_profile:update_platform_preferences" %}', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
                    body: JSON.stringify(this.platform)
                });
                const data = await res.json();
                this.showAlert(data.success ? 'success' : 'error', data.success ? 'Preferences saved!' : data.error);
            } catch (e) {
                this.showAlert('error', 'Network error');
            }
            this.loading = false;
        },

        async saveWallet() {
            this.loading = true;
            try {
                const res = await fetch('{% url "user_profile:update_wallet_settings" %}', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
                    body: JSON.stringify(this.wallet)
                });
                const data = await res.json();
                this.showAlert(data.success ? 'success' : 'error', data.success ? 'Settings saved!' : data.error);
            } catch (e) {
                this.showAlert('error', 'Network error');
            }
            this.loading = false;
        },

        deleteAccount() {
            if (confirm('This action cannot be undone! Are you absolutely sure?')) {
                alert('Account deletion requires admin approval. Please contact support.');
            }
        },

        showAlert(type, message) {
            this.alert = { show: true, type, message, icon: type === 'success' ? '✅' : '❌' };
            setTimeout(() => this.alert.show = false, 5000);
        }
    }
}
</script>
{% endblock %}
'''

if __name__ == '__main__':
    output_path = 'templates/user_profile/profile/settings.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(SETTINGS_TEMPLATE)
    print(f'✅ Created {output_path} ({len(SETTINGS_TEMPLATE)} bytes)')
    print(f'   Lines: {SETTINGS_TEMPLATE.count(chr(10))}')
    print('   Sections: Profile, Privacy, Notifications, Platform, Wallet, Account')
    print('   Features: Alpine.js state management, async API calls, optimistic UI')

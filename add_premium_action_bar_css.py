"""Add premium Action Bar CSS"""

css_code = """

/* ==========================================
   PREMIUM ACTION BAR - GAME THEMED
   ========================================== */

.action-bar-premium {
    background: transparent;
    padding: 30px 0;
    margin-bottom: 40px;
    position: relative;
    z-index: 50;
}

.action-card-premium {
    background: linear-gradient(135deg, rgba(20, 27, 45, 0.95) 0%, rgba(10, 14, 39, 0.98) 100%);
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(20px);
    position: relative;
    overflow: hidden;
}

/* Game-specific accents */
.action-card-premium.game-efootball::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, #00ff88 0%, #00d4ff 100%);
}

.action-card-premium.game-valorant::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, #ff4655 0%, #fd4556 100%);
}

.action-main {
    position: relative;
}

/* Status Header for Registered Users */
.action-status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px;
    border-radius: 30px;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.5px;
}

.status-confirmed {
    background: rgba(0, 255, 136, 0.15);
    color: #00ff88;
    border: 2px solid rgba(0, 255, 136, 0.3);
}

.status-pending {
    background: rgba(255, 193, 7, 0.15);
    color: #ffc107;
    border: 2px solid rgba(255, 193, 7, 0.3);
    animation: pendingPulse 2s ease-in-out infinite;
}

@keyframes pendingPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.registration-date {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-muted);
    font-size: 13px;
    font-weight: 600;
}

/* Premium Dashboard Button */
.btn-dashboard-premium {
    display: block;
    position: relative;
    padding: 0;
    border-radius: 16px;
    text-decoration: none;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.btn-dashboard-premium:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.btn-glow {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, transparent 0%, rgba(255, 255, 255, 0.1) 50%, transparent 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.btn-dashboard-premium:hover .btn-glow {
    opacity: 1;
    animation: shine 1.5s ease-in-out infinite;
}

@keyframes shine {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

.btn-content {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 24px 32px;
    position: relative;
    z-index: 1;
}

/* Game-specific button styles */
.btn-dashboard-premium.game-efootball .btn-content {
    background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%);
}

.btn-dashboard-premium.game-valorant .btn-content {
    background: linear-gradient(135deg, #ff4655 0%, #fd4556 100%);
}

.btn-dashboard-premium.game-efootball:hover .btn-content {
    background: linear-gradient(135deg, #00d4ff 0%, #00ff88 100%);
}

.btn-dashboard-premium.game-valorant:hover .btn-content {
    background: linear-gradient(135deg, #fd4556 0%, #ff4655 100%);
}

.btn-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 12px;
    font-size: 28px;
    color: #000;
    flex-shrink: 0;
}

.btn-text {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.btn-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.7);
}

.btn-title {
    font-size: 22px;
    font-weight: 900;
    font-family: 'Rajdhani', sans-serif;
    color: #000;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.btn-arrow {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 50%;
    font-size: 20px;
    color: #000;
    transition: transform 0.3s ease;
}

.btn-dashboard-premium:hover .btn-arrow {
    transform: translateX(8px);
}

/* Action Features */
.action-features {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.feature-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    transition: all 0.3s ease;
}

.feature-item:hover {
    background: rgba(0, 255, 136, 0.1);
    color: var(--accent-green);
    transform: translateY(-2px);
}

.feature-item i {
    font-size: 16px;
    color: var(--accent-green);
}

/* Register Button */
.btn-register-premium {
    display: block;
    position: relative;
    padding: 0;
    border-radius: 16px;
    text-decoration: none;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.btn-register-premium:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 60px rgba(0, 255, 136, 0.4);
}

.btn-register-premium.game-efootball .btn-content {
    background: linear-gradient(135deg, #00ff88 0%, #00d46e 100%);
}

.btn-register-premium.game-valorant .btn-content {
    background: linear-gradient(135deg, #ff4655 0%, #fd4556 100%);
}

.action-header-register {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
}

.register-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    background: rgba(0, 255, 136, 0.15);
    border: 2px solid rgba(0, 255, 136, 0.3);
    border-radius: 30px;
    color: var(--accent-green);
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 1px;
}

.urgency-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    background: rgba(255, 71, 87, 0.15);
    border: 2px solid rgba(255, 71, 87, 0.3);
    border-radius: 30px;
    color: var(--accent-red);
    font-weight: 700;
    font-size: 13px;
    animation: urgencyPulse 1.5s ease-in-out infinite;
}

@keyframes urgencyPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

.register-benefits {
    display: flex;
    gap: 20px;
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.benefit-item {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 600;
}

.benefit-item i {
    color: var(--accent-green);
    font-size: 14px;
}

/* Closed State */
.action-closed {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 32px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    border: 1px dashed rgba(255, 255, 255, 0.2);
}

.closed-icon {
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 50%;
    font-size: 28px;
    color: var(--text-muted);
}

.closed-text h3 {
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 6px;
    color: var(--text-primary);
}

.closed-text p {
    font-size: 14px;
    color: var(--text-muted);
    margin: 0;
}

/* Login Button */
.btn-login-premium {
    display: block;
    position: relative;
    padding: 0;
    border-radius: 16px;
    text-decoration: none;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.btn-login-premium .btn-content {
    background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
}

.btn-login-premium:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 60px rgba(0, 212, 255, 0.4);
}

.action-header-login {
    margin-bottom: 20px;
}

.login-message {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 20px;
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 10px;
    color: var(--accent-blue);
    font-size: 14px;
    font-weight: 600;
}

/* Responsive Design */
@media (max-width: 768px) {
    .action-card-premium {
        padding: 24px;
    }
    
    .action-status-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;
    }
    
    .btn-content {
        padding: 20px 24px;
        gap: 16px;
    }
    
    .btn-icon {
        width: 48px;
        height: 48px;
        font-size: 24px;
    }
    
    .btn-title {
        font-size: 18px;
    }
    
    .action-features {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .register-benefits {
        flex-direction: column;
        gap: 12px;
    }
    
    .action-header-register {
        flex-direction: column;
        align-items: flex-start;
    }
}

@media (max-width: 480px) {
    .action-features {
        grid-template-columns: 1fr;
    }
    
    .btn-arrow {
        width: 40px;
        height: 40px;
        font-size: 18px;
    }
}

/* Remove old styles */
.action-bar-wrapper {
    display: block;
}

.action-bar-left,
.action-bar-right {
    display: none;
}
"""

with open(r'G:\My Projects\WORK\DeltaCrown\static\tournaments\css\tournament-detail-modern.css', 'a', encoding='utf-8') as f:
    f.write(css_code)

print("✅ Premium Action Bar CSS added!")
print("✅ Game-themed colors implemented")
print("✅ Dashboard button styling complete")
print("✅ Professional spacing and padding")

/**
 * TEAM MODULE DEBUG SCRIPT
 * Run this in your browser console (F12) to verify all features are working
 */

console.log('🔍 STARTING TEAM MODULE DEBUG...\n');

// =============================================================================
// TEST 1: TEAM CREATE PAGE DEBUG
// =============================================================================
function debugTeamCreate() {
    console.log('=== TEAM CREATE PAGE DEBUG ===');
    
    // Check if on correct page
    if (!window.location.pathname.includes('/teams/create')) {
        console.warn('⚠️  Not on team create page. Navigate to /teams/create/ first.');
        return false;
    }
    
    // Check form exists
    const form = document.getElementById('team-create-form');
    console.log('✅ Form exists:', !!form);
    
    // Check Step 1 elements
    console.log('\n--- STEP 1 ELEMENTS ---');
    const step1 = document.querySelector('.form-step[data-step="1"]');
    console.log('✅ Step 1 container:', !!step1);
    console.log('✅ Step 1 visible:', step1?.classList.contains('active'));
    
    const nameInput = document.getElementById('id_name');
    const tagInput = document.getElementById('id_tag');
    const mottoInput = document.getElementById('id_tagline');
    const descInput = document.getElementById('id_description');
    const descCounter = document.getElementById('desc-count');
    
    console.log('✅ Name input:', !!nameInput, nameInput?.value || '(empty)');
    console.log('✅ Tag input:', !!tagInput, tagInput?.value || '(empty)');
    console.log('✅ Motto input:', !!mottoInput, mottoInput?.value || '(empty)');
    console.log('✅ Description textarea:', !!descInput);
    console.log('✅ Character counter:', !!descCounter, descCounter?.textContent || '');
    
    // Check validation status elements
    console.log('\n--- VALIDATION ELEMENTS ---');
    console.log('✅ Name status:', !!document.getElementById('name-status'));
    console.log('✅ Tag status:', !!document.getElementById('tag-status'));
    
    // Check buttons
    console.log('\n--- NAVIGATION BUTTONS ---');
    const nextBtn = document.querySelector('.btn-next');
    console.log('✅ Next button:', !!nextBtn);
    
    // Check other steps exist
    console.log('\n--- OTHER STEPS ---');
    console.log('✅ Step 2 exists:', !!document.querySelector('.form-step[data-step="2"]'));
    console.log('✅ Step 3 exists:', !!document.querySelector('.form-step[data-step="3"]'));
    console.log('✅ Step 4 exists:', !!document.querySelector('.form-step[data-step="4"]'));
    
    // Check JavaScript class loaded
    console.log('\n--- JAVASCRIPT ---');
    console.log('✅ EsportsTeamCreate class:', typeof EsportsTeamCreate);
    console.log('✅ Wizard instance:', window.teamWizard ? 'Initialized' : 'Not found');
    
    if (window.teamWizard) {
        console.log('   Current step:', window.teamWizard.currentStep);
        console.log('   Form data:', window.teamWizard.formData);
    }
    
    // Test step navigation manually
    console.log('\n--- MANUAL STEP TEST ---');
    if (window.teamWizard) {
        console.log('📝 Testing step navigation...');
        const originalStep = window.teamWizard.currentStep;
        
        // Try going to step 2
        window.teamWizard.showStep(2);
        const step2Visible = !!document.querySelector('.form-step[data-step="2"].active');
        console.log('   Step 2 navigation:', step2Visible ? '✅ WORKS' : '❌ FAILED');
        
        // Go back to original step
        window.teamWizard.showStep(originalStep);
        console.log('   Returned to step', originalStep);
    }
    
    console.log('\n✅ TEAM CREATE DEBUG COMPLETE\n');
    return true;
}

// =============================================================================
// TEST 2: TEAM DETAIL PAGE DEBUG
// =============================================================================
function debugTeamDetail() {
    console.log('=== TEAM DETAIL PAGE DEBUG ===');
    
    // Check if on correct page
    if (!window.location.pathname.includes('/teams/') || window.location.pathname.includes('/create')) {
        console.warn('⚠️  Not on team detail page. Navigate to /teams/{slug}/ first.');
        return false;
    }
    
    // Check tabs
    console.log('\n--- TABS ---');
    const tabs = document.querySelectorAll('.tab[data-tab]');
    console.log('✅ Tabs found:', tabs.length);
    tabs.forEach(tab => {
        const tabName = tab.getAttribute('data-tab');
        const isActive = tab.classList.contains('active');
        console.log(`   - ${tabName}: ${isActive ? 'Active' : 'Inactive'}`);
    });
    
    // Check Team Hub specifically
    console.log('\n--- TEAM HUB ---');
    const teamHubTab = document.querySelector('.tab[data-tab="team-hub"]');
    const teamHubSection = document.getElementById('tab-team-hub');
    
    if (teamHubTab) {
        console.log('✅ Team Hub tab:', 'FOUND');
        console.log('   Visible:', teamHubTab.offsetParent !== null);
        console.log('   Active:', teamHubTab.classList.contains('active'));
    } else {
        console.warn('❌ Team Hub tab: NOT FOUND (you may not be a member)');
    }
    
    if (teamHubSection) {
        console.log('✅ Team Hub section:', 'FOUND');
        console.log('   Hidden class:', teamHubSection.classList.contains('hidden'));
        
        // Count feature cards in Team Hub
        const cards = teamHubSection.querySelectorAll('.bg-white');
        console.log('✅ Feature cards:', cards.length, '(expected: 6)');
        
        // Check specific buttons
        console.log('\n--- TEAM HUB BUTTONS ---');
        const updateGameIdBtn = teamHubSection.querySelector('[onclick*="updateGameID"]');
        const notificationsBtn = teamHubSection.querySelector('[onclick*="showTeamNotifications"]');
        const leaveTeamBtn = teamHubSection.querySelector('[onclick*="initLeave"]');
        
        console.log('✅ Update Game ID button:', !!updateGameIdBtn);
        console.log('✅ Notifications button:', !!notificationsBtn);
        console.log('✅ Leave Team button:', !!leaveTeamBtn);
    } else {
        console.warn('❌ Team Hub section: NOT FOUND');
    }
    
    // Check tab switching functionality
    console.log('\n--- TAB SWITCHING TEST ---');
    if (teamHubTab && teamHubSection) {
        console.log('📝 Testing tab switch...');
        teamHubTab.click();
        
        setTimeout(() => {
            const isVisible = !teamHubSection.classList.contains('hidden');
            console.log('   After click:', isVisible ? '✅ VISIBLE' : '❌ STILL HIDDEN');
            console.log('   Active tab:', document.querySelector('.tab.active')?.getAttribute('data-tab'));
        }, 100);
    }
    
    console.log('\n✅ TEAM DETAIL DEBUG COMPLETE\n');
    return true;
}

// =============================================================================
// TEST 3: TEAM LIST PAGE DEBUG
// =============================================================================
function debugTeamList() {
    console.log('=== TEAM LIST PAGE DEBUG ===');
    
    if (!window.location.pathname.includes('/teams') || window.location.pathname.includes('/create')) {
        console.warn('⚠️  Not on team list page. Navigate to /teams/ first.');
        return false;
    }
    
    console.log('\n--- TEAM CARDS ---');
    const cards = document.querySelectorAll('.team-card-premium');
    console.log('✅ Team cards found:', cards.length);
    
    if (cards.length > 0) {
        const firstCard = cards[0];
        console.log('\n--- FIRST CARD INSPECTION ---');
        console.log('✅ Has onclick:', !!firstCard.getAttribute('onclick'));
        console.log('✅ Has cursor pointer:', firstCard.style.cursor === 'pointer');
        console.log('✅ Onclick content:', firstCard.getAttribute('onclick')?.substring(0, 50) + '...');
        
        // Check join button
        const joinBtn = firstCard.querySelector('[onclick*="initJoin"]');
        if (joinBtn) {
            console.log('✅ Join button:', 'FOUND');
            console.log('   Has stopPropagation:', joinBtn.getAttribute('onclick')?.includes('stopPropagation'));
        }
    }
    
    console.log('\n✅ TEAM LIST DEBUG COMPLETE\n');
    return true;
}

// =============================================================================
// TEST 4: CONSOLE ERROR CHECK
// =============================================================================
function checkConsoleErrors() {
    console.log('=== CONSOLE ERROR CHECK ===');
    console.log('📝 Check the console above for any errors (red text)');
    console.log('📝 Check the Network tab (F12) for any 404 errors');
    console.log('✅ If no red errors above, console is clean!\n');
}

// =============================================================================
// TEST 5: STATIC FILES CHECK
// =============================================================================
function checkStaticFiles() {
    console.log('=== STATIC FILES CHECK ===');
    
    const checks = [
        { name: 'Team Create JS', url: '/static/teams/js/team-create-esports.js' },
        { name: 'Team Create CSS', url: '/static/teams/css/team-create-esports.css' },
        { name: 'Team Join JS', url: '/static/teams/js/team-join-modern.js' },
        { name: 'Team Leave JS', url: '/static/teams/js/team-leave-modern.js' },
        { name: 'Teams Detail JS', url: '/static/siteui/js/teams-detail.js' },
    ];
    
    console.log('📝 Checking static file availability...\n');
    
    checks.forEach(check => {
        fetch(check.url)
            .then(response => {
                if (response.ok) {
                    console.log(`✅ ${check.name}: LOADED`);
                } else {
                    console.error(`❌ ${check.name}: ${response.status} ${response.statusText}`);
                }
            })
            .catch(error => {
                console.error(`❌ ${check.name}: FAILED -`, error.message);
            });
    });
    
    console.log('\n✅ STATIC FILES CHECK COMPLETE\n');
}

// =============================================================================
// MASTER FUNCTION - RUN ALL TESTS
// =============================================================================
function runAllTests() {
    console.clear();
    console.log('🚀 RUNNING COMPLETE TEAM MODULE DEBUG\n');
    console.log('═'.repeat(80) + '\n');
    
    // Check current page
    const path = window.location.pathname;
    console.log('📍 Current page:', path);
    console.log('');
    
    // Run appropriate tests
    if (path.includes('/teams/create')) {
        debugTeamCreate();
    } else if (path.match(/\/teams\/[^\/]+\/?$/)) {
        debugTeamDetail();
    } else if (path === '/teams/' || path === '/teams') {
        debugTeamList();
    } else {
        console.warn('⚠️  Unknown page. Navigate to one of:');
        console.log('   - /teams/create/ (team create)');
        console.log('   - /teams/{slug}/ (team detail)');
        console.log('   - /teams/ (team list)');
    }
    
    // Always check console and static files
    console.log('═'.repeat(80) + '\n');
    checkConsoleErrors();
    checkStaticFiles();
    
    console.log('═'.repeat(80));
    console.log('🎉 DEBUG COMPLETE!');
    console.log('═'.repeat(80));
}

// =============================================================================
// AUTO-RUN ON LOAD
// =============================================================================
console.log('🔧 Team Module Debug Script Loaded');
console.log('📝 Available commands:');
console.log('   - runAllTests()          → Run complete debug suite');
console.log('   - debugTeamCreate()      → Debug team create page');
console.log('   - debugTeamDetail()      → Debug team detail page');
console.log('   - debugTeamList()        → Debug team list page');
console.log('   - checkStaticFiles()     → Check if files loaded');
console.log('');
console.log('💡 TIP: Type runAllTests() and press Enter\n');

// Auto-run after 1 second
setTimeout(() => {
    console.log('🤖 Auto-running tests in 2 seconds...');
    console.log('⏸️  (Reload page to cancel)\n');
    
    setTimeout(runAllTests, 2000);
}, 1000);

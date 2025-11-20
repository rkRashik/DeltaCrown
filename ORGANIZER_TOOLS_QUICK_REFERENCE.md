# Quick Reference: Organizer Tools

**For Tournament Organizers** - How to use the new management features

---

## 🎯 Accessing the Organizer Console

1. Navigate to `/tournaments/organizer/` to see your tournament dashboard
2. Click on any tournament to open the management hub
3. Use the tabs to switch between: Overview | Participants | Payments | Brackets | Disputes | Announcements | Settings

---

## 👥 Participant Management (FE-T-022)

### Bulk Approve Registrations
1. Go to **Participants** tab
2. Check the boxes next to pending registrations
3. Click **"Approve Selected"** button (appears when items are selected)
4. Confirm the action
5. Selected registrations will be changed to "Confirmed" status

### Bulk Reject Registrations
1. Go to **Participants** tab
2. Check the boxes next to pending registrations
3. Click **"Reject Selected"** button
4. Enter rejection reason (optional)
5. Confirm the action
6. Participants will receive rejection status

### Disqualify a Participant
1. Find the confirmed participant in the list
2. Click the **🚫 Disqualify** button
3. Enter disqualification reason (required)
4. Confirm the action
5. Participant will be marked as disqualified with reason stored

### Export Roster
1. Go to **Participants** tab
2. Click **"Export CSV"** button
3. File downloads: `{tournament-slug}_roster_{date}.csv`
4. Contains: ID, Username, Email, Team, Status, Registration Date, Check-in Status

---

## 💰 Payment Management (FE-T-023)

### Bulk Verify Payments
1. Go to **Payments** tab
2. Check the boxes next to submitted payments
3. Click **"Verify Selected"** button (appears when items are selected)
4. Confirm the action
5. Selected payments will be marked as verified

### Process a Refund
1. Find the verified payment in the list
2. Click the **🔄 Refund** button
3. Enter refund amount (can be partial or full)
4. Enter refund reason (required)
5. Enter refund method (manual/bkash/nagad)
6. Confirm the action
7. Payment status changes to "Refunded"

### View Payment History
1. Find any payment in the list
2. Click the **🕒 History** button
3. Popup window shows all payments for that participant
4. Includes: ID, Amount, Method, Status, Submission date

### Export Payment Report
1. Go to **Payments** tab
2. Click **"Export CSV"** button
3. File downloads: `{tournament-slug}_payments_{date}.csv`
4. Contains: ID, Username, Amount, Method, Status, Timestamps, Verifier

---

## 🏆 Match Management (FE-T-024)

### Reschedule a Match
1. Go to **Brackets** tab
2. Find the match you want to reschedule
3. Click **"Reschedule"** (or use match action menu)
4. Enter new scheduled time (format: YYYY-MM-DD HH:MM)
5. Enter reason for rescheduling (optional)
6. Confirm the action
7. Match time is updated, old time stored in audit trail

### Mark Match as Forfeit
1. Find the match to forfeit
2. Click **"Forfeit"** button
3. Select which participant is forfeiting (1 or 2)
4. Enter forfeit reason (required)
5. Confirm the action
6. Match marked as completed with forfeit score (1-0 or 0-1)
7. Winner automatically assigned (opposite of forfeiting participant)

### Override Match Score
1. Find a **completed** match
2. Click **"Override Score"** button
3. Enter new score for participant 1
4. Enter new score for participant 2
5. Enter override reason (required)
6. Confirm the action
7. Score updated, winner recalculated, old scores stored in audit trail

### Cancel a Match
1. Find the match to cancel
2. Click **"Cancel"** button
3. Enter cancellation reason (required)
4. Confirm the action
5. Match status changes to "Cancelled"

---

## ⚡ Quick Tips

### Keyboard Shortcuts
- **Select All**: Click the checkbox in the table header
- **Deselect All**: Click the "Select All" checkbox again

### Bulk Action Tips
- Bulk buttons only appear when items are selected
- You can select items across multiple pages (but refresh clears selection)
- Always review selections before confirming bulk actions

### CSV Export Tips
- Export includes all data regardless of current filters
- Filename includes tournament slug and date for easy organization
- Open in Excel/Google Sheets for analysis and pivot tables

### Audit Trail
- All destructive actions (disqualify, refund, override, forfeit, cancel) are logged
- Check the database `metadata` fields for complete audit trails
- Includes: action type, reason, timestamp, who performed it, old/new values

### Permission Levels
- **Superuser/Staff**: Full access to all organizer tools
- **Tournament Organizer**: Access to their own tournaments
- **Regular Users**: No access to organizer console (redirected)

---

## 🚨 Common Issues & Solutions

### "Permission Denied" Error
- **Cause**: You don't have organizer permissions for this tournament
- **Solution**: Contact a superuser to grant you tournament staff permissions

### Bulk Actions Not Working
- **Cause**: No items selected
- **Solution**: Check the checkboxes next to items first

### CSV Export Opens in Browser Instead of Downloading
- **Cause**: Browser settings
- **Solution**: Right-click the "Export CSV" button → "Save Link As"

### Payment History Popup Blocked
- **Cause**: Browser popup blocker
- **Solution**: Allow popups for this site in browser settings

### Datetime Format Errors
- **Cause**: Invalid date format when rescheduling
- **Solution**: Use format: YYYY-MM-DD HH:MM (e.g., 2025-11-25 14:30)

---

## 📞 Support

For technical issues or feature requests:
- Check the documentation in `/docs/`
- Review audit trails in database for action history
- Contact system administrator for permission issues

---

**Last Updated**: November 20, 2025  
**Version**: Sprint 7 Complete  
**Status**: Production Ready

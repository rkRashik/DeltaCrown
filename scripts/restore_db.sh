#!/bin/bash
# =============================================================================
# Database Restore Script for DeltaCrown
# =============================================================================
# This script restores a PostgreSQL database from a backup file.
#
# Usage:
#   ./scripts/restore_db.sh <backup_file>
#   ./scripts/restore_db.sh backups/deltacrown_backup_20250104_123456.sql
#   ./scripts/restore_db.sh backups/deltacrown_backup_20250104_123456.sql.gz
#
# WARNING: This will DROP and recreate the database!
# =============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
fi

# Database configuration
DB_USER="${POSTGRES_USER:-deltacrown}"
DB_NAME="${POSTGRES_DB:-deltacrown}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

# =============================================================================
# Functions
# =============================================================================

print_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[0;33m[WARNING]\033[0m $1"
}

# Check if backup file exists
check_backup_file() {
    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    print_success "Backup file found: $BACKUP_FILE"
}

# Decompress if needed
decompress_backup() {
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        print_info "Decompressing backup file..."
        DECOMPRESSED_FILE="${BACKUP_FILE%.gz}"
        
        if gunzip -c "$BACKUP_FILE" > "$DECOMPRESSED_FILE"; then
            BACKUP_FILE="$DECOMPRESSED_FILE"
            TEMP_FILE=true
            print_success "Backup decompressed"
        else
            print_error "Failed to decompress backup"
            exit 1
        fi
    fi
}

# Confirm restore action
confirm_restore() {
    print_warning "========================================="
    print_warning "WARNING: This will DROP the database!"
    print_warning "Database: $DB_NAME"
    print_warning "Host: ${DB_HOST}:${DB_PORT}"
    print_warning "========================================="
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        print_info "Restore cancelled"
        exit 0
    fi
}

# Check PostgreSQL connection
check_postgres_connection() {
    print_info "Checking PostgreSQL connection..."
    
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
        print_error "Cannot connect to PostgreSQL"
        exit 1
    fi
    
    print_success "PostgreSQL connection successful"
}

# Create backup before restore
create_safety_backup() {
    print_info "Creating safety backup of current database..."
    
    SAFETY_BACKUP="${PROJECT_ROOT}/backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
    
    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -f "$SAFETY_BACKUP" 2>/dev/null; then
        
        print_success "Safety backup created: $SAFETY_BACKUP"
    else
        print_warning "Could not create safety backup (database may not exist)"
    fi
}

# Restore database
restore_database() {
    print_info "Restoring database from backup..."
    
    # Restore using psql
    if PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -f "$BACKUP_FILE" >/dev/null 2>&1; then
        
        print_success "Database restored successfully"
    else
        print_error "Failed to restore database"
        print_info "You may need to restore from the safety backup: $SAFETY_BACKUP"
        exit 1
    fi
}

# Run Django migrations
run_migrations() {
    print_info "Running Django migrations..."
    
    cd "$PROJECT_ROOT"
    
    if python manage.py migrate --no-input; then
        print_success "Migrations completed"
    else
        print_warning "Migrations failed, but database was restored"
    fi
}

# Cleanup temp files
cleanup() {
    if [ "${TEMP_FILE:-false}" = true ] && [ -f "$BACKUP_FILE" ]; then
        print_info "Cleaning up temporary files..."
        rm -f "$BACKUP_FILE"
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_info "========================================="
    print_info "DeltaCrown Database Restore"
    print_info "========================================="
    echo ""
    
    # Check arguments
    if [ $# -eq 0 ]; then
        print_error "Usage: $0 <backup_file>"
        print_info "Example: $0 backups/deltacrown_backup_20250104_123456.sql"
        exit 1
    fi
    
    BACKUP_FILE="$1"
    TEMP_FILE=false
    
    # Check requirements
    if ! command -v psql &> /dev/null; then
        print_error "psql is not installed"
        exit 1
    fi
    
    # Execute restore steps
    check_backup_file
    decompress_backup
    check_postgres_connection
    confirm_restore
    create_safety_backup
    restore_database
    run_migrations
    cleanup
    
    echo ""
    print_success "========================================="
    print_success "Database restored successfully!"
    print_success "========================================="
}

# Trap cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"

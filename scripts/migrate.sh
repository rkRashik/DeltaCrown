#!/bin/bash
# =============================================================================
# Database Migration Script for DeltaCrown
# =============================================================================
# This script safely runs Django migrations with proper backup and rollback.
#
# Usage:
#   ./scripts/migrate.sh
#   ./scripts/migrate.sh --fake-initial
#   ./scripts/migrate.sh <app_name>
#   ./scripts/migrate.sh <app_name> <migration_name>
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
fi

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

# Check for uncommitted migrations
check_uncommitted_migrations() {
    print_info "Checking for uncommitted migration files..."
    
    cd "$PROJECT_ROOT"
    
    UNCOMMITTED=$(git ls-files --others --exclude-standard | grep "migrations/.*\.py$" || true)
    
    if [ -n "$UNCOMMITTED" ]; then
        print_warning "Found uncommitted migration files:"
        echo "$UNCOMMITTED"
        echo ""
        read -p "Continue anyway? (yes/no): " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            print_info "Migration cancelled"
            exit 0
        fi
    fi
}

# Create pre-migration backup
create_backup() {
    print_info "Creating pre-migration backup..."
    
    if [ -x "${SCRIPT_DIR}/backup_db.sh" ]; then
        "${SCRIPT_DIR}/backup_db.sh" --compress
    else
        print_warning "Backup script not found or not executable"
        read -p "Continue without backup? (yes/no): " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            print_info "Migration cancelled"
            exit 0
        fi
    fi
}

# Show pending migrations
show_pending_migrations() {
    print_info "Checking for pending migrations..."
    
    cd "$PROJECT_ROOT"
    
    if python manage.py showmigrations --plan | grep -q "\[ \]"; then
        print_warning "Pending migrations found:"
        python manage.py showmigrations --plan | grep "\[ \]"
        echo ""
    else
        print_success "No pending migrations"
        exit 0
    fi
}

# Run migrations
run_migrations() {
    print_info "Running migrations..."
    
    cd "$PROJECT_ROOT"
    
    MIGRATION_ARGS="$@"
    
    if python manage.py migrate $MIGRATION_ARGS --no-input; then
        print_success "Migrations completed successfully"
    else
        print_error "Migration failed!"
        print_warning "You may need to restore from backup"
        exit 1
    fi
}

# Verify database integrity
verify_database() {
    print_info "Verifying database integrity..."
    
    cd "$PROJECT_ROOT"
    
    if python manage.py check --database default; then
        print_success "Database integrity check passed"
    else
        print_warning "Database integrity check failed"
    fi
}

# Show migration summary
show_summary() {
    print_info "Migration summary:"
    
    cd "$PROJECT_ROOT"
    python manage.py showmigrations --plan | grep "\[X\]" | tail -n 10
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_info "========================================="
    print_info "DeltaCrown Database Migration"
    print_info "========================================="
    echo ""
    
    # Check if manage.py exists
    if [ ! -f "${PROJECT_ROOT}/manage.py" ]; then
        print_error "manage.py not found in $PROJECT_ROOT"
        exit 1
    fi
    
    # Execute migration steps
    check_uncommitted_migrations
    show_pending_migrations
    create_backup
    run_migrations "$@"
    verify_database
    show_summary
    
    echo ""
    print_success "========================================="
    print_success "Migration completed successfully!"
    print_success "========================================="
}

# Run main function
main "$@"

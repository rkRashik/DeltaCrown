#!/bin/bash
# =============================================================================
# Database Backup Script for DeltaCrown
# =============================================================================
# This script creates a backup of the PostgreSQL database and stores it
# with a timestamp in the backups directory.
#
# Usage:
#   ./scripts/backup_db.sh
#   ./scripts/backup_db.sh --compress
#
# Environment Variables Required:
#   POSTGRES_USER - Database user
#   POSTGRES_DB - Database name
#   POSTGRES_PASSWORD - Database password (optional if using .pgpass)
# =============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
COMPRESS=false

# Load environment variables from .env if it exists
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
fi

# Check for compression flag
if [ "${1:-}" = "--compress" ]; then
    COMPRESS=true
fi

# Database configuration
DB_USER="${POSTGRES_USER:-deltacrown}"
DB_NAME="${POSTGRES_DB:-deltacrown}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

# Backup configuration
BACKUP_PREFIX="deltacrown_backup"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_PREFIX}_${TIMESTAMP}.sql"
MAX_BACKUPS=30  # Keep last 30 backups

# =============================================================================
# Functions
# =============================================================================

# Print colored messages
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

# Create backup directory if it doesn't exist
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        print_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

# Check if PostgreSQL is accessible
check_postgres_connection() {
    print_info "Checking PostgreSQL connection..."
    
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
        print_error "Cannot connect to PostgreSQL at ${DB_HOST}:${DB_PORT}"
        print_info "Make sure PostgreSQL is running and accessible"
        exit 1
    fi
    
    print_success "PostgreSQL connection successful"
}

# Create database backup
create_backup() {
    print_info "Creating database backup..."
    print_info "Database: $DB_NAME"
    print_info "Backup file: $BACKUP_FILE"
    
    # Use pg_dump to create backup
    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        -f "$BACKUP_FILE"; then
        
        print_success "Database backup created successfully"
    else
        print_error "Failed to create database backup"
        exit 1
    fi
}

# Compress backup if requested
compress_backup() {
    if [ "$COMPRESS" = true ]; then
        print_info "Compressing backup..."
        
        if gzip "$BACKUP_FILE"; then
            BACKUP_FILE="${BACKUP_FILE}.gz"
            print_success "Backup compressed: $BACKUP_FILE"
        else
            print_warning "Failed to compress backup, keeping uncompressed version"
        fi
    fi
}

# Get backup file size
get_backup_size() {
    if [ -f "$BACKUP_FILE" ]; then
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_info "Backup size: $SIZE"
    fi
}

# Clean old backups (keep last N backups)
cleanup_old_backups() {
    print_info "Cleaning up old backups (keeping last $MAX_BACKUPS)..."
    
    # Count existing backups
    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}/${BACKUP_PREFIX}"* 2>/dev/null | wc -l)
    
    if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
        # Delete oldest backups
        DELETE_COUNT=$((BACKUP_COUNT - MAX_BACKUPS))
        ls -1t "${BACKUP_DIR}/${BACKUP_PREFIX}"* | tail -n "$DELETE_COUNT" | xargs rm -f
        print_success "Deleted $DELETE_COUNT old backup(s)"
    else
        print_info "No old backups to delete ($BACKUP_COUNT/$MAX_BACKUPS)"
    fi
}

# Create backup metadata
create_metadata() {
    METADATA_FILE="${BACKUP_FILE}.meta"
    
    cat > "$METADATA_FILE" << EOF
Backup Metadata
================
Database: $DB_NAME
Host: $DB_HOST:$DB_PORT
User: $DB_USER
Timestamp: $(date)
Backup File: $(basename "$BACKUP_FILE")
Compressed: $COMPRESS
Django Version: $(python -c "import django; print(django.__version__)" 2>/dev/null || echo "Unknown")
EOF
    
    print_info "Metadata saved to: $METADATA_FILE"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_info "========================================="
    print_info "DeltaCrown Database Backup"
    print_info "========================================="
    echo ""
    
    # Check requirements
    if ! command -v pg_dump &> /dev/null; then
        print_error "pg_dump is not installed"
        exit 1
    fi
    
    # Execute backup steps
    create_backup_dir
    check_postgres_connection
    create_backup
    compress_backup
    get_backup_size
    create_metadata
    cleanup_old_backups
    
    echo ""
    print_success "========================================="
    print_success "Backup completed successfully!"
    print_success "========================================="
    print_info "Backup location: $BACKUP_FILE"
    
    # Show recent backups
    echo ""
    print_info "Recent backups:"
    ls -lht "${BACKUP_DIR}/${BACKUP_PREFIX}"* 2>/dev/null | head -n 5
}

# Run main function
main "$@"

#!/usr/bin/env bash
set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
BACKUP_DIR="$SCRIPT_DIR/.backups"

# Function to create backup
create_backup() {
  local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
  local backup_path="$BACKUP_DIR/$backup_name"
  
  mkdir -p "$backup_path"
  
  header "🔒 Creating Backup: $backup_name"
  
  # Backup local VS Code files if they exist
  if [ -f "$LOCAL_PATH/workbench.desktop.main.css" ]; then
    info "Backing up local VS Code files..."
    sudo cp "$LOCAL_PATH/workbench.desktop.main.css" "$backup_path/" 2>/dev/null || true
    
    # Backup original CSS without font imports
    sudo grep -v '@import "nerdFonts.css";' "$LOCAL_PATH/workbench.desktop.main.css" > "$backup_path/workbench.desktop.main.css.original" 2>/dev/null || true
    
    success "Local VS Code files backed up"
  fi
  
  # Save backup metadata
  cat > "$backup_path/metadata.json" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_name": "$backup_name",
  "vs_code_path": "$LOCAL_PATH"
}
EOF
  
  success "Backup created: $backup_path"
  echo "$backup_name"
}

# Function to list backups
list_backups() {
  header "📚 Available Backups"
  echo ""
  
  if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    warning "No backups found"
    return 1
  fi
  
  local i=1
  for backup in "$BACKUP_DIR"/*; do
    if [ -d "$backup" ]; then
      local name=$(basename "$backup")
      local timestamp=$(jq -r '.timestamp' "$backup/metadata.json" 2>/dev/null || echo "Unknown")
      echo "  $i) $name (Created: $timestamp)"
      ((i++))
    fi
  done
}

# Function to restore backup
restore_backup() {
  local backup_name="$1"
  local backup_path="$BACKUP_DIR/$backup_name"
  
  if [ ! -d "$backup_path" ]; then
    error "Backup not found: $backup_name"
    return 1
  fi
  
  header "🔄 Restoring Backup: $backup_name"
  
  # Restore local VS Code files
  if [ -f "$backup_path/workbench.desktop.main.css.original" ]; then
    info "Restoring local VS Code files..."
    sudo cp "$backup_path/workbench.desktop.main.css.original" "$LOCAL_PATH/workbench.desktop.main.css"
    success "Local VS Code files restored"
  fi
  
  # Remove font files
  info "Removing installed font files..."
  sudo rm -f "$LOCAL_PATH/nerdFonts.css" 2>/dev/null || true
  sudo rm -rf "$LOCAL_PATH"/*/  2>/dev/null || true
  
  success "Backup restored successfully"
  warning "Restart VS Code for changes to take effect"
}

# Main menu
case "${1:-}" in
  create)
    create_backup
    ;;
  list)
    list_backups
    ;;
  restore)
    if [ -z "${2:-}" ]; then
      list_backups
      echo ""
      read -p "Enter backup name to restore: " backup_name
    else
      backup_name="$2"
    fi
    restore_backup "$backup_name"
    ;;
  *)
    echo "Usage: $0 {create|list|restore [backup_name]}"
    echo ""
    echo "Commands:"
    echo "  create  - Create a new backup before installing fonts"
    echo "  list    - List all available backups"
    echo "  restore - Restore VS Code to a previous state"
    exit 1
    ;;
esac
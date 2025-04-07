#!/bin/bash
# Get the directory of this script.
DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$DIR/dist/prs"

# Define candidate directories (in order of preference).
candidates=(
  "/home/user/.local/bin"
  "$HOME/.local/bin"
  "/usr/local/bin"
  "/usr/bin"
  "/opt/bin"
)

destination=""

# Iterate over candidate directories.
for d in "${candidates[@]}"; do
    if [ -d "$d" ]; then
        destination="$d/prs"
        break
    else
        # Try to create the directory.
        if mkdir -p "$d" 2>/dev/null; then
            destination="$d/prs"
            break
        else
            # If normal mkdir fails, try with sudo.
            sudo mkdir -p "$d" && { destination="$d/prs"; break; }
        fi
    fi
done

if [ -z "$destination" ]; then
    echo "No suitable destination directory found. Please create one and add it to your PATH."
    exit 1
fi

echo "Copying binary to $destination"
# Check if the destination directory is writable.
if [ -w "$(dirname "$destination")" ]; then
    cp "$BINARY" "$destination"
else
    sudo cp "$BINARY" "$destination"
fi

echo "Installation complete. You can now run 'prs' from anywhere."

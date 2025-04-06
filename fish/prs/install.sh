#!/bin/bash

# Paths
SOURCE="$(dirname "$0")/prs.fish"
TARGET="$HOME/.config/fish/functions/prs.fish"
ENV_TARGET="$HOME/.prs.env"

# Create target directory if it doesn't exist
mkdir -p "$(dirname "$TARGET")"

# Check if target function already exists
if [ -f "$TARGET" ]; then
    read -p "Function already exists at $TARGET. Overwrite? [y/N]: " confirm
    case "$confirm" in
        [yY][eE][sS]|[yY])
            echo "...Overwriting $TARGET..."
            cp "$SOURCE" "$TARGET"
            chmod 644 "$TARGET"
            ;;
        *)
            echo "❌ Install cancelled."
            exit 1
            ;;
    esac
else
    cp "$SOURCE" "$TARGET"
    chmod 644 "$TARGET"
fi

echo "✅ Function copied to: $TARGET"

# Handle env file
if [ -f "$ENV_TARGET" ]; then
    echo "✅ Env file detected: $ENV_TARGET"
else
    echo "- Creating env file at $ENV_TARGET"
    cat <<EOF > "$ENV_TARGET"
REPO="anchorlabsinc/anchorage"
USERNAME="@me"

CHECK_ONLY=0
CHECK_DETAILED=1
REVIEWS_ONLY=0
REVIEWS_DETAILED=1
LABELS_ONLY=0
LABELS_DETAILED=1

SHOW_URL=1
SHOW_BRANCH=1
SHOW_DRAFTS=0
EOF
    chmod 644 "$ENV_TARGET"
fi

# Instruction to load the function immediately in current Fish shell
echo
echo "To load it now in your terminal, run:"
echo
echo "    functions -c prs prs           "
echo
echo "Or restart the terminal / open a new Fish shell."

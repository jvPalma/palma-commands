#!/usr/bin/env bash

echo "Testing input handling..."
if [ -t 0 ]; then
  echo "Interactive mode detected"
  read -p "Enter choice: " choice
else
  echo "Non-interactive mode detected"  
  read choice
fi

echo "You entered: '$choice'"

case $choice in
  3)
    echo "Choice 3 selected!"
    ;;
  *)
    echo "Other choice: $choice"
    ;;
esac
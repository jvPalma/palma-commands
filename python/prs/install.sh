#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
sudo cp "$DIR/dist/prs" /usr/local/bin/prs
sudo cp "$DIR/dist/prs" /home/user/bin
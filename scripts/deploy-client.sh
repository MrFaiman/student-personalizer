#!/bin/bash

# --- CONFIGURATION ---
REPO="MrFaiman/student-personalizer"  # Updated with your repo name
ARTIFACT_NAME="client-build-files"   # Must match the name in your YAML
TARGET_DIR="/var/www/demo.upvote.co.il/html"    # Where the files should live
TEMP_DIR="/tmp/demo.upvote.co.il/html"        # Temporary staging area
# ---------------------

echo "Starting deployment..."

# 1. Create/Clean Temp Directory
echo "Cleaning temporary files..."
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

# 2. Download the latest artifact
# We use 'gh' to find the latest run and download the specific artifact
echo "Downloading latest artifact from GitHub..."
gh run download --repo $REPO --name $ARTIFACT_NAME --dir $TEMP_DIR

# Check if download succeeded
if [ -z "$(ls -A $TEMP_DIR)" ]; then
   echo "Error: Artifact not found or download failed."
   exit 1
fi

# 3. Deploy files to /var/www
echo "Moving files to $TARGET_DIR..."

# Create target dir if it doesn't exist
sudo mkdir -p $TARGET_DIR

# Remove old files (Safety first: we use rsync or rm)
sudo rm -rf $TARGET_DIR/*

# Move new files (The artifact usually unzips automatically or contains the folder structure)
# If the artifact contains a 'dist' folder inside, you might need $TEMP_DIR/dist/*
sudo cp -r $TEMP_DIR/* $TARGET_DIR/

# 4. Fix Permissions
# Assuming you use Nginx/Apache, usually the user is 'www-data'
echo "Fixing permissions..."
sudo chown -R www-data:www-data $TARGET_DIR
sudo chmod -R 755 $TARGET_DIR

# 5. Cleanup
echo "Cleaning up..."
rm -rf $TEMP_DIR

echo "Deployment Complete! version deployed to $TARGET_DIR"

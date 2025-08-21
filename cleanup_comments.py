#!/usr/bin/env python3
"""
Script to clean up obvious comments from Python files while preserving essential ones.
"""

import os
import re
from pathlib import Path

def should_keep_comment(comment_line):
    """Determine if a comment should be kept."""
    comment_text = comment_line.strip()
    
    # Keep empty lines
    if not comment_text:
        return True
    
    if comment_text == "#":
        return False
    
    # Keep docstrings (triple quotes)
    if '"""' in comment_text or "'''" in comment_text:
        return True
    
    # Keep important markers
    important_markers = [
        "TODO", "FIXME", "NOTE", "WARNING", "IMPORTANT", "CRITICAL",
        "XXX", "HACK", "BUG", "OPTIMIZE"
    ]
    if any(marker in comment_text.upper() for marker in important_markers):
        return True
    
    # Keep copyright/license comments
    if any(word in comment_text.lower() for word in ["copyright", "license", "author"]):
        return True
    
    # Keep shebang
    if comment_text.startswith("#!"):
        return True
    
    obvious_patterns = [
        r"# Initialize",
        r"# Create",
        r"# Setup",
        r"# Configure",
        r"# Set up",
        r"# Get ",
        r"# Store ",
        r"# Save ",
        r"# Load ",
        r"# Read ",
        r"# Write ",
        r"# Send ",
        r"# Handle ",
        r"# Process ",
        r"# Generate ",
        r"# Update ",
        r"# Check ",
        r"# Validate ",
        r"# Parse ",
        r"# Extract ",
        r"# Download ",
        r"# Upload ",
        r"# Clean up",
        r"# Cleanup",
        r"# Add ",
        r"# Remove ",
        r"# Delete ",
        r"# Clear ",
        r"# Reset ",
        r"# Start ",
        r"# Stop ",
        r"# End ",
        r"# Begin ",
        r"# Finish ",
        r"# Complete ",
        r"# Cancel ",
        r"# Skip ",
        r"# Return ",
        r"# Show ",
        r"# Display ",
        r"# Print ",
        r"# Log ",
        r"# Debug ",
        r"# Error ",
        r"# Success ",
        r"# Fail ",
        r"# Try ",
        r"# Attempt ",
        r"# Wait ",
        r"# Delay ",
        r"# Sleep ",
        r"# Pause ",
        r"# Continue ",
        r"# Proceed ",
        r"# Next ",
        r"# Previous ",
        r"# First ",
        r"# Last ",
        r"# Final ",
        r"# Main ",
        r"# Primary ",
        r"# Secondary ",
        r"# Helper ",
        r"# Utility ",
        r"# Service ",
        r"# Router ",
        r"# Handler ",
        r"# Callback ",
        r"# Function ",
        r"# Method ",
        r"# Class ",
        r"# Module ",
        r"# Package ",
        r"# Import ",
        r"# Export ",
        r"# Define ",
        r"# Declare ",
        r"# Assign ",
        r"# Set ",
        r"# Bind ",
        r"# Connect ",
        r"# Disconnect ",
        r"# Open ",
        r"# Close ",
        r"# File ",
        r"# Directory ",
        r"# Path ",
        r"# URL ",
        r"# API ",
        r"# HTTP ",
        r"# Request ",
        r"# Response ",
        r"# Data ",
        r"# Text ",
        r"# Content ",
        r"# Message ",
        r"# User ",
        r"# Session ",
        r"# State ",
        r"# Context ",
        r"# Config ",
        r"# Settings ",
        r"# Options ",
        r"# Parameters ",
        r"# Arguments ",
        r"# Values ",
        r"# Results ",
        r"# Output ",
        r"# Input ",
        r"# Format ",
        r"# Type ",
        r"# Mode ",
        r"# Status ",
        r"# Flag ",
        r"# Variable ",
        r"# Constant ",
        r"# Global ",
        r"# Local ",
        r"# Temporary ",
        r"# Temp ",
        r"# Cache ",
        r"# Buffer ",
        r"# Queue ",
        r"# Stack ",
        r"# List ",
        r"# Array ",
        r"# Dict ",
        r"# Map ",
        r"# Object ",
        r"# Instance ",
        r"# Reference ",
        r"# Pointer ",
        r"# Link ",
        r"# Connection ",
        r"# Database ",
        r"# Table ",
        r"# Record ",
        r"# Field ",
        r"# Column ",
        r"# Row ",
        r"# Index ",
        r"# Key ",
        r"# Value ",
        r"# Pair ",
        r"# Tuple ",
        r"# String ",
        r"# Number ",
        r"# Integer ",
        r"# Float ",
        r"# Boolean ",
        r"# Date ",
        r"# Time ",
        r"# Timestamp ",
        r"# ID ",
        r"# UUID ",
        r"# Hash ",
        r"# Token ",
        r"# Secret ",
        r"# Password ",
        r"# Username ",
        r"# Email ",
        r"# Phone ",
        r"# Address ",
        r"# Name ",
        r"# Title ",
        r"# Description ",
        r"# Comment ",
        r"# Note ",
        r"# Info ",
        r"# Details ",
        r"# Summary ",
        r"# Report ",
        r"# Log ",
        r"# Event ",
        r"# Action ",
        r"# Command ",
        r"# Query ",
        r"# Search ",
        r"# Filter ",
        r"# Sort ",
        r"# Order ",
        r"# Group ",
        r"# Batch ",
        r"# Chunk ",
        r"# Block ",
        r"# Section ",
        r"# Part ",
        r"# Piece ",
        r"# Fragment ",
        r"# Segment ",
        r"# Element ",
        r"# Item ",
        r"# Entry ",
        r"# Record ",
        r"# Document ",
        r"# Template ",
        r"# Sample ",
        r"# Example ",
        r"# Test ",
        r"# Mock ",
        r"# Fake ",
        r"# Dummy ",
        r"# Placeholder"
    ]
    
    for pattern in obvious_patterns:
        if re.match(pattern, comment_text, re.IGNORECASE):
            return False
    
    # Keep business logic comments (longer than simple descriptive comments)
    if len(comment_text) > 50 and not any(comment_text.lower().startswith(word) for word in 
                                         ["# create", "# initialize", "# setup", "# configure"]):
        return True
    
    # Keep comments that explain WHY, not WHAT
    why_indicators = ["because", "since", "due to", "reason", "why", "purpose", "goal"]
    if any(indicator in comment_text.lower() for indicator in why_indicators):
        return True
    
    # Keep section dividers and headers
    if len(comment_text) > 20 and ("=" in comment_text or "-" in comment_text or 
                                   comment_text.isupper() or 
                                   comment_text.endswith(":")):
        return True
    
    # Default: remove simple descriptive comments
    return False

def clean_file_comments(file_path):
    """Clean comments from a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            
            # If it's a comment line
            if stripped.startswith('#'):
                if should_keep_comment(line):
                    cleaned_lines.append(line)
                # else: skip the line (remove it)
            else:
                cleaned_lines.append(line)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        return True
    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False

def main():
    """Main function to clean up comments in all Python files."""
    workspace = Path("/workspace")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(workspace):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"Found {len(python_files)} Python files to clean")
    
    cleaned_count = 0
    for file_path in python_files:
        print(f"Cleaning: {file_path}")
        if clean_file_comments(file_path):
            cleaned_count += 1
    
    print(f"Successfully cleaned {cleaned_count} files")

if __name__ == "__main__":
    main()
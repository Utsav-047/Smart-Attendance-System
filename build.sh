#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "===> Upgrading pip..."
python -m pip install --upgrade pip

echo "===> Pre-installing build tools..."
python -m pip install cmake wheel setuptools

echo "===> Enforcing single-core build limit to prevent Render 8GB OOM crash..."
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS="-j1"

echo "===> Installing pre-compiled dlib-bin binary wheel..."
python -m pip install dlib-bin

echo "===> Installing all application dependencies from requirements.txt..."
python -m pip install -r requirements.txt

echo "===> Build completed successfully!"

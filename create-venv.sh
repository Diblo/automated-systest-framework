#!/usr/bin/env sh
set -e

# --- Global Configuration Variables ---
PROJECT_ROOT="$(pwd)"

PATH_VENV="${PROJECT_ROOT}/.venv"
MODE=0 # 0=Development (Default), 1=Production

##############################################
# Argument Parsing
##############################################
parse_args() {
  while [ $# -gt 0 ]; do
    arg="$1"
    case ${arg} in
      --create-production)
        MODE=1

        if [ -z "$2" ] || echo "$2" | grep -q '^-'; then
          echo "Error: --create-production requires a path argument." >&2
          exit 1
        fi

        PATH_VENV="$2"
        shift
        ;;
      -h | --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "OPTIONS:"
        echo "  --create-production <PATH>   Creates a production-ready venv at the specified PATH."
        echo "  -h, --help                   Show this help message and exit."
        exit 0
        ;;
      *)
        echo "Unknown argument: ${arg}" >&2
        exit 1
        ;;
    esac
    shift
  done
}

##############################################
# Virtual Environment Creation
##############################################
create_virtual_environment() {
  # 1. Ensure Python 3.8 is available
  if ! command -v python3.8 > /dev/null 2>&1; then
    echo "Error: python3.8 not found. Please install Python 3.8." >&2
    exit 1
  fi

  if ! python3.8 -c "import venv" > /dev/null 2>&1; then
    echo "Error: python3.8 venv module not found. Please install Python 3.8 venv module." >&2
    exit 1
  fi

  echo "Creating Python 3.8 virtual environment at '${PATH_VENV}'..."

  if [ -d "${PATH_VENV}" ]; then
    echo "Warning: '${PATH_VENV}' exists. Updating..."
  else
    mkdir -p "$(dirname "${PATH_VENV}")"
  fi

  if [ "${MODE}" -eq 0 ]; then
    python3.8 -m venv "${PATH_VENV}"
  else
    python3.8 -m venv --copies "${PATH_VENV}"
  fi

  echo "Upgrading wheel..."
  "${PATH_VENV}/bin/pip" install --upgrade wheel==0.45.1
}

##############################################
# Dependency Installation
##############################################
install_dependencies() {
  # Ensure script is run from project root
  if [ ! -f "setup.py" ]; then
    echo "Error: Run this script from the project root (requires setup.py)." >&2
    exit 1
  fi

  echo "Installing project dependencies..."
  if [ "${MODE}" -eq 0 ]; then
    # Local development: editable install (-e)
    "${PATH_VENV}/bin/pip" install -e .
  else
    # Production (MODE 1)
    "${PATH_VENV}/bin/pip" install --no-cache-dir .
  fi
}

##############################################
# Main Execution
##############################################
if [ ! -f "setup.py" ] || [ ! -d "src" ]; then
  echo "Error: Run this script from the project root (requires setup.py and src/ directories)." >&2
  exit 1
fi

parse_args "$@"

create_virtual_environment
install_dependencies

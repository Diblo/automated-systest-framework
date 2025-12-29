#!/usr/bin/env sh
set -e

# --- Configuration ---
BUILD_OUTPUT_DIR="build"

# Fetch metadata from project files in the original directory
SOURCE_NAME=$(grep -E '^Source: ' debian/control | head -n1 | awk '{print $2}')

# --- Global variables ---
WORK_DIR_PATH=$(pwd)
ARTIFACTS_PATH="${WORK_DIR_PATH}/${BUILD_OUTPUT_DIR}"

SKIP_UPDATE=0
SKIP_TOOL=0
SKIP_DEP=0
VERSION=""
DATETIME=$(date +%Y%m%d-%H%M%S)
OS_CODENAME=$(sed -n "s/^VERSION_CODENAME=//p" /etc/os-release)

##############################################
# Argument Parsing
##############################################
parse_args() {
  while [ $# -gt 0 ]; do
    arg="$1"
    case ${arg} in
      --version)
        # Check if argument exists and is not another flag
        if [ -z "$2" ] || echo "$2" | grep -q '^-'; then
          echo "Error: --version requires a version number argument (e.g., 1.0.0)." >&2
          exit 1
        fi

        # Strip the leading 'v' if present
        VERSION="${2#v}"

        # POSIX pattern validation (checks for X.Y.Z format)
        case "${VERSION}" in
          [0-9]*.[0-9]*.[0-9]*) ;;
          *)
            echo "Error: Version format '$2' is invalid. Expected format is X.Y.Z or vX.Y.Z." >&2
            exit 1
            ;;
        esac
        shift
        ;;
      --os-codename)
        # Check if argument exists and is not another flag
        if [ -z "$2" ] || echo "$2" | grep -q '^-'; then
          echo "Error: --os-codename requires a name argument (e.g., focal)." >&2
          exit 1
        fi
        OS_CODENAME="${2}"
        shift
        ;;
      --no-update)
        SKIP_UPDATE=1
        ;;
      --no-tool)
        SKIP_TOOL=1
        ;;
      --no-dep)
        SKIP_DEP=1
        ;;
      --no-install)
        SKIP_UPDATE=1
        SKIP_TOOL=1
        SKIP_DEP=1
        ;;
      -h | --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "OPTIONS:"
        echo "  --version         Specifies the package version number (Required)."
        echo "  --os-codename     Specifies an OS codename (e.g., focal, jammy)."
        echo "  --no-update       Skip 'apt update'."
        echo "  --no-tool         Skip installing build tools."
        echo "  --no-dep          Skip installing application build dependencies."
        echo "  --no-install      Skip all installation steps (apt update, build tools, and dependencies)."
        echo "  -h, --help        Show this help message and exit."
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
# Prepare
##############################################
prepare() {
  # 1. Initial check for requirements
  if [ -z "${VERSION}" ]; then
    echo "Error: The --version option is required." >&2
    exit 1
  fi

  if [ ! -d "debian" ] || [ ! -d "src" ]; then
    echo "Error: Run this script from the project root (requires debian/ and src/ directories)." >&2
    exit 1
  fi

  if [ -z "${SOURCE_NAME}" ]; then
    echo "Error: Source Name is missing." >&2
    exit 1
  fi

  # 2. Handle APT Update
  # (Only runs if not explicitly skipped, and if tools or dependencies need installation)
  if [ "${SKIP_UPDATE}" -eq 0 ] && { [ "${SKIP_TOOL}" -eq 0 ] || [ "${SKIP_DEP}" -eq 0 ]; }; then
    echo "Running 'apt update'..."
    apt update || exit 1
  else
    echo "Skipping 'apt update'."
  fi

  # 3. Install Script Tools
  if [ "${SKIP_TOOL}" -eq 0 ]; then
    echo "Installing script tools..."
    apt install -y devscripts equivs rsync || exit 1
  else
    echo "Skipping installation of script tools."
  fi

  # 4. Setup environment
  echo "Creating new artifact directories..."
  mkdir -p "${ARTIFACTS_PATH}"
  mkdir "${ARTIFACTS_PATH}/${SOURCE_NAME}-${VERSION}-${DATETIME}"

  echo "Copying source to temporary build directory: '${ARTIFACTS_PATH}/${SOURCE_NAME}-${VERSION}-${DATETIME}'..."
  # Copy project files, excluding the build, .venv, and .git dir
  rsync -a --exclude "/${BUILD_OUTPUT_DIR}" --exclude "/.venv" --exclude "/.git" "${WORK_DIR_PATH}/" \
    "${ARTIFACTS_PATH}/${SOURCE_NAME}-${VERSION}-${DATETIME}/"

  # 5. Change to the temporary source folder
  cd "${ARTIFACTS_PATH}/${SOURCE_NAME}-${VERSION}-${DATETIME}" || (echo "Unable to switch to source dir" >&2 && exit 1)
  echo "Switched PWD to: $(pwd)"
}

##############################################
# Build Debian package
##############################################
build_package() {
  # 1. Install Build Dependencies
  if [ "${SKIP_DEP}" -eq 0 ]; then
    echo "Installing dependencies..."
    # Installs application build dependencies using mk-build-deps
    yes | mk-build-deps -i -r debian/control || exit 1
  else
    echo "Skipping dependencies."
  fi

  echo "Building Debian package..."

  # 2. Inject VERSION file
  echo "Updating VERSION file to ${VERSION}..."
  echo "${VERSION}" > src/systest/VERSION

  # 3. Update changelog with the new version and timestamp
  debchange -v "${VERSION}-${DATETIME}" -p -D "${OS_CODENAME}" -m "Append timestamp when binarydeb was built."

  # 4. Ensure debian/rules is executable before running dpkg-buildpackage
  chmod +x debian/rules

  # 5. Build the package
  # dpkg-buildpackage places artifacts in the parent directory: ../ (which is $BUILD_OUTPUT_DIR)
  dpkg-buildpackage -us -uc
}

##############################################
# Main Execution
##############################################
parse_args "$@"

prepare
build_package

# shellcheck disable=2154
if [ -n "${SUDO_USER}" ]; then
  chown "${SUDO_USER}": -R "${ARTIFACTS_PATH}"
fi

echo "Build complete! All artifacts are located in '${BUILD_OUTPUT_DIR}'."

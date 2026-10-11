#!/usr/bin/env bash
#
# Build the AWS Lambda deployment artifact.
#
# Produces build/bot_package.zip containing the application code plus
# runtime-only dependencies compiled for the Lambda x86_64 / manylinux2014
# platform. The archive root contains main.py so that the configured Lambda
# handler (main.handler) resolves correctly.
#
# Usage:
#   ./build.sh                 # targets Python 3.13 (matches .python-version)
#   PYTHON_VERSION=3.13 ./build.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
PACKAGE_DIR="${BUILD_DIR}/package"
ZIP_PATH="${BUILD_DIR}/bot_package.zip"

# Lambda runtime configuration. Must match the `runtime` value in terraform.
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
ABI_TAG="cp${PYTHON_VERSION//./}"
PLATFORM="${PLATFORM:-manylinux2014_x86_64}"

if [[ ! -f "${ROOT_DIR}/requirements-lambda.txt" ]]; then
  echo "error: requirements-lambda.txt not found" >&2
  exit 1
fi

echo "==> Cleaning previous build output"
rm -rf "${PACKAGE_DIR}" "${ZIP_PATH}"
mkdir -p "${PACKAGE_DIR}"

echo "==> Installing runtime dependencies for ${PLATFORM} (cpython ${PYTHON_VERSION})"
python3 -m pip install \
  --quiet \
  --upgrade \
  --requirement "${ROOT_DIR}/requirements-lambda.txt" \
  --target "${PACKAGE_DIR}" \
  --platform "${PLATFORM}" \
  --python-version "${PYTHON_VERSION}" \
  --implementation cp \
  --abi "${ABI_TAG}" \
  --only-binary=:all:

echo "==> Copying application code"
cp "${ROOT_DIR}/main.py" "${PACKAGE_DIR}/"
cp -R "${ROOT_DIR}/handlers" "${ROOT_DIR}/utils" "${PACKAGE_DIR}/"

echo "==> Pruning bytecode and build noise"
find "${PACKAGE_DIR}" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
find "${PACKAGE_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "${PACKAGE_DIR}" -type d \( -name "test" -o -name "tests" \) -prune -exec rm -rf {} +

echo "==> Creating ${ZIP_PATH}"
(
  cd "${PACKAGE_DIR}"
  zip -q -r -X "${ZIP_PATH}" .
)

ZIP_SIZE_MB=$(( $(stat -c%s "${ZIP_PATH}") / 1024 / 1024 ))
echo "==> Artifact ready: ${ZIP_PATH} (${ZIP_SIZE_MB} MB)"

if (( ZIP_SIZE_MB >= 50 )); then
  cat >&2 <<'EOF'
warning: the artifact is 50 MB or larger.
Lambda's direct zip upload (terraform `filename`) is limited to 50 MB.
Upload the zip to S3 and switch the aws_lambda_function resource to use
`s3_bucket`/`s3_key` instead of `filename`.
EOF
fi

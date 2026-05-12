#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# build.sh  — sestaví a otaguje Docker image sysnetcz/dictionaries
#
# Použití:
#   ./build.sh                    # sestaví lokálně
#   ./build.sh --push             # sestaví a pushne do registru
#   ./build.sh --registry ghcr.io/sysnetcz --push
#   ./build.sh --version 2.1.0    # přebije verzi z VERSION souboru
#   ./build.sh --no-latest        # netag jako :latest
#   ./build.sh --platform linux/amd64,linux/arm64 --push  # multi-arch
#
# Tagovací strategie (SemVer):
#   2.1.3  → sysnetcz/dictionaries:2.1.3   (immutable — konkrétní release)
#            sysnetcz/dictionaries:2.1      (latest patch tohoto minoru)
#            sysnetcz/dictionaries:2        (latest minor tohoto majoru)
#            sysnetcz/dictionaries:latest   (nejnovější stabilní verze)
# ---------------------------------------------------------------------------
set -euo pipefail

# ---------- výchozí hodnoty -------------------------------------------------
REGISTRY=""
IMAGE_NAME="sysnetcz/dictionaries"
PUSH=false
LATEST=true
PLATFORM=""
OVERRIDE_VERSION=""

# ---------- parsování argumentů --------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --push)        PUSH=true; shift ;;
        --no-latest)   LATEST=false; shift ;;
        --registry)    REGISTRY="$2"; shift 2 ;;
        --version)     OVERRIDE_VERSION="$2"; shift 2 ;;
        --platform)    PLATFORM="$2"; shift 2 ;;
        -h|--help)
            sed -n '3,20p' "$0"
            exit 0 ;;
        *)
            echo "Neznámý argument: $1" >&2
            exit 1 ;;
    esac
done

# ---------- verze -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/VERSION"

if [[ -n "${OVERRIDE_VERSION}" ]]; then
    VERSION="${OVERRIDE_VERSION}"
elif [[ -f "${VERSION_FILE}" ]]; then
    VERSION="$(cat "${VERSION_FILE}" | tr -d '[:space:]')"
else
    echo "CHYBA: Soubor VERSION nenalezen a --version nebyl zadán." >&2
    exit 1
fi

# Validace SemVer (MAJOR.MINOR.PATCH)
if ! [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "CHYBA: Verze '${VERSION}' není platný SemVer (očekáváno MAJOR.MINOR.PATCH)." >&2
    exit 1
fi

IFS='.' read -r MAJOR MINOR PATCH <<< "${VERSION}"

# ---------- sestavení tagů -------------------------------------------------
BASE="${IMAGE_NAME}"
if [[ -n "${REGISTRY}" ]]; then
    BASE="${REGISTRY}/${IMAGE_NAME}"
fi

TAG_FULL="${BASE}:${VERSION}"          # 2.1.3
TAG_MINOR="${BASE}:${MAJOR}.${MINOR}"  # 2.1
TAG_MAJOR="${BASE}:${MAJOR}"           # 2
TAG_LATEST="${BASE}:latest"

# ---------- metadata pro OCI labely ----------------------------------------
BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

# ---------- výpis plánu ----------------------------------------------------
echo "============================================="
echo " SYSNET Dictionaries — Docker build"
echo "============================================="
echo " Verze:       ${VERSION}"
echo " Build date:  ${BUILD_DATE}"
echo " Git commit:  ${VCS_REF}"
echo " Image:       ${TAG_FULL}"
echo " Tagy:        ${TAG_FULL}"
echo "              ${TAG_MINOR}"
echo "              ${TAG_MAJOR}"
[[ "${LATEST}" == "true" ]] && echo "              ${TAG_LATEST}"
[[ -n "${PLATFORM}" ]] && echo " Platform:    ${PLATFORM}"
echo " Push:        ${PUSH}"
echo "============================================="
echo ""

# ---------- sestavení -------------------------------------------------------
BUILD_ARGS=(
    --build-arg "DICT_VERSION=${VERSION}"
    --build-arg "BUILD_DATE=${BUILD_DATE}"
    --build-arg "VCS_REF=${VCS_REF}"
    --tag "${TAG_FULL}"
    --tag "${TAG_MINOR}"
    --tag "${TAG_MAJOR}"
)

[[ "${LATEST}" == "true" ]] && BUILD_ARGS+=(--tag "${TAG_LATEST}")

if [[ -n "${PLATFORM}" ]]; then
    BUILD_ARGS+=(--platform "${PLATFORM}")
    [[ "${PUSH}" == "true" ]] && BUILD_ARGS+=(--push) || BUILD_ARGS+=(--load)
    docker buildx build "${BUILD_ARGS[@]}" "${SCRIPT_DIR}"
else
    docker build "${BUILD_ARGS[@]}" "${SCRIPT_DIR}"
    if [[ "${PUSH}" == "true" ]]; then
        echo ""
        echo "--- Pushing ${TAG_FULL} ---"
        docker push "${TAG_FULL}"
        docker push "${TAG_MINOR}"
        docker push "${TAG_MAJOR}"
        [[ "${LATEST}" == "true" ]] && docker push "${TAG_LATEST}"
    fi
fi

echo ""
echo "✓ Build dokončen: ${TAG_FULL}"

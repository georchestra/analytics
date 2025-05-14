#!/bin/bash
set -e
# Build a docker image from the Pypi repo
# Will only work just after publishing the package with `tox -e publish`
# VERSION need to match the packages's version.

DOCKER_IMAGE_NAME=georchestra/analytics-cli
#VERSION=$(git describe --tags --dirty --always)

#########################
# The command line help #
#########################
display_help() {
    echo "Usage: $0" >&2
    echo
    echo "   --mode=[dev,test,release]  build mode"
    echo "   --version=              With dev mode, can be arbitrary, will be the image tag. "
    echo "                           With test and release mode, must match an existing version on the corresponding pypi repo. "
    echo "                           It will also be the image's tag. "
    echo
    exit 1
}
if [ "$#" -eq 0 ]
then
    display_help >&2
    exit 0
fi


for i in "$@"; do
  case $i in
    --mode=*)
      MODE="${i#*=}"
      shift # past argument=value
      ;;
    --version=*)
      VERSION="${i#*=}"
      shift # past argument=value
      ;;
    --help)
      display_help
      exit 0
      ;;
    -*|--*)
      echo "Unknown option $i"
      exit 1
      ;;
    *)
      ;;
  esac
done

case $MODE in
    dev)
      printf "Building a dev image based on your local code. \nYou can force the version with --version= option \n"
      if [[ "$VERSION" == "" ]]; then
        VERSION=$(git describe --tags --dirty --always)
      fi
    ;;
    test)
      echo "Building a test image based on test.pypi.org repo. You can choose the version with --version= option"
    ;;
    release)
      echo "Building a release image based on pypi.org repo. You can choose the version with --version= option"
    ;;
    *)
      echo "unknown mode. Exiting"
      exit 1
      ;;
esac
#echo docker build --build-arg "VERSION=${VERSION}" -f Dockerfile --target $MODE -t "${DOCKER_IMAGE_NAME}:${VERSION}" .

docker build \
    --build-arg "VERSION=${VERSION}" \
    -f Dockerfile \
    --target $MODE \
    -t "${DOCKER_IMAGE_NAME}:${VERSION}" \
    .
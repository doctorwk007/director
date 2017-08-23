#!/bin/bash

set -xe

scriptDir=$(cd $(dirname $0) && pwd)


make_docs()
{
  cd $TRAVIS_BUILD_DIR/build/src/director-build
  make python-coverage
  make docs-doxygen 2>&1 > log.txt || cat log.txt
  make docs-sphinx-generate 2>&1 > log.txt || cat log.txt
  make docs-sphinx-build 2>&1 > log.txt || cat log.txt

  cd $TRAVIS_BUILD_DIR/docs
  mv $TRAVIS_BUILD_DIR/docs/sphinx/_build/html sphinx_docs
  mv $TRAVIS_BUILD_DIR/build/src/director-build/docs/doxygen/html doxygen_docs
  mv $TRAVIS_BUILD_DIR/build/src/director-build/python-coverage/html python_coverage

  tar -czf sphinx_docs.tar.gz sphinx_docs
  tar -czf doxygen_docs.tar.gz doxygen_docs
  tar -czf python_coverage.tar.gz python_coverage

  $scriptDir/bintray_upload.sh $TRAVIS_BUILD_DIR/docs/*.tar.gz
}

make_linux_package()
{
  cd $TRAVIS_BUILD_DIR/distro/package
  ./make_linux_package.sh 2>&1 > log.txt || cat log.txt
  $scriptDir/bintray_upload.sh $TRAVIS_BUILD_DIR/distro/package/*.tar.gz
}

make_mac_package()
{
  cd $TRAVIS_BUILD_DIR/distro/package
  ./make_mac_package.sh 2>&1 > log.txt || cat log.txt
  $scriptDir/bintray_upload.sh $TRAVIS_BUILD_DIR/distro/package/*.tar.gz
}

make_package()
{
  if [ "$TRAVIS_OS_NAME" = "linux" ]; then
    make_linux_package
  elif [ "$TRAVIS_OS_NAME" = "osx" ]; then
    make_mac_package
  fi
}

run_docker_deploy()
{
  cd $TRAVIS_BUILD_DIR/distro/package
  tar_name=$(ls director*.tar.gz)
  package_name=$(echo ${tar_name} | sed s/\.tar\.gz//)
  cp ${tar_name} /tmp
  cd $TRAVIS_BUILD_DIR
  rm -rf *
  tar -zxf /tmp/${tar_name}
  rm /tmp/${tar_name}
  ln -s $PWD/${package_name} ./install
}

run_branch_commands()
{
  if [ "$MAKE_DOCS" = "ON" ]; then
    make_docs
  fi

  if [ "$MAKE_PACKAGE" = "ON" ]; then
    make_package
  fi

  if [ "$DOCKER_DEPLOY" = "true" ]; then
    run_docker_deploy
  fi
}

# these commands run for branches but not for pull requests
if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
  run_branch_commands
fi

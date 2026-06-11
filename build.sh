#!/bin/sh
# Windows-form path so the generated linkfile uses C:/... which the native
# wlalink.exe can open (a /c/... linkfile path fails at link time).
export PVSNESLIB_HOME=C:/tools/pvsneslib
export PATH=$PVSNESLIB_HOME/devkitsnes/bin:$PVSNESLIB_HOME/devkitsnes/tools:$PATH
cd /c/dev/snesgame2
make "$@"

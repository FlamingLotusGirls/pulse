#!/bin/bash

set -e
cd $(dirname $0)

# Assume OPC is checked out to the same top-level directory as the soma repo
OPC_DIR=../../../openpixelcontrol

set -x
make -C $OPC_DIR
exec $OPC_DIR/bin/gl_server points.json 7890 model.stl

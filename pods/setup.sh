#!/bin/bash

rm -rf vendor
mkdir vendor
cd vendor
git clone git@github.com:FlamingLotusGirls/openpixelcontrol.git
cd openpixelcontrol
make

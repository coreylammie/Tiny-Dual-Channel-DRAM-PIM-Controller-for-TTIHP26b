#!/usr/bin/env sh
set -eu

python -m pytest test/test_model.py test/test_dense_layer_demo.py
(
  cd test
  make clean
  make
)

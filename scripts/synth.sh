#!/usr/bin/env sh
set -eu

LIBRELANE_ROOT="${LIBRELANE_ROOT:-/Users/coreylammie/librelane}"
NIX_SHELL="${NIX_SHELL:-/nix/var/nix/profiles/default/bin/nix-shell}"
PDK="${PDK:-ihp-sg13g2}"
RUN_TAG="${RUN_TAG:-stage3b-config-control-synth}"

if [ ! -x "$NIX_SHELL" ]; then
  echo "nix-shell not found at $NIX_SHELL" >&2
  exit 127
fi

if [ ! -f "$LIBRELANE_ROOT/shell.nix" ]; then
  echo "LibreLane shell.nix not found at $LIBRELANE_ROOT/shell.nix" >&2
  exit 127
fi

TO_STEP="${TO_STEP:-Yosys.Synthesis}"

exec "$NIX_SHELL" "$LIBRELANE_ROOT/shell.nix" --run \
  "python -m librelane --pdk $PDK --flow classic --to $TO_STEP --run-tag $RUN_TAG --overwrite config.yaml"

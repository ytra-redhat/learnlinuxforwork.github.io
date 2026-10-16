#!/bin/bash
# One entry point; locate the repository independently of the current directory.
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
"$ROOT/scripts/build-local-lab.sh" --provider vmware "$@"
STATUS=$?
printf '\n'
if [ "$STATUS" -ne 0 ]; then
  printf 'De installatie is gestopt. Lees de melding hierboven.\n'
fi
if [ -t 0 ]; then
  read -r -p 'Druk op Enter om dit venster te sluiten. ' _
fi
exit "$STATUS"

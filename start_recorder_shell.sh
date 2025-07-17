#!/bin/bash
# Autostart CLI in debug user shell

cd /recorder_fixer || exit 1
exec python3 ./cli.py

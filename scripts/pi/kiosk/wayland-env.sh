#!/usr/bin/env bash
# Resolve the labwc Wayland socket so systemd-launched helpers can talk to the
# compositor. Sourced by the kiosk scripts; sets XDG_RUNTIME_DIR + WAYLAND_DISPLAY.

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  for _sock in "$XDG_RUNTIME_DIR"/wayland-*; do
    case "$_sock" in *.lock) continue ;; esac
    if [ -S "$_sock" ]; then
      WAYLAND_DISPLAY="$(basename "$_sock")"
      export WAYLAND_DISPLAY
      break
    fi
  done
  unset _sock
fi

#!/bin/bash
# SessionStart hook: clears all context guard sentinels and state.
rm -f /tmp/claude-context-warned-* /tmp/claude-context-pct

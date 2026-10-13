"""Recognising an agent that stopped because the subscription's usage limit was reached.

Once the limit is hit every new agent fails within seconds, so a run that keeps launching turns
hundreds of problems into failures that say nothing about the problems. The agent stages check
each failed attempt's log with this and stop launching as soon as one shows the limit.
"""
import re

# What Claude Code prints when a session, usage or weekly limit stops it, with the reset time.
PATTERN = re.compile(r"hit your (?:session|usage|weekly) limit[^\n]*", re.I)


def limit_message(log_path):
    """The limit message from the latest attempt in this log, or None if it was not the limit."""
    try:
        text = open(log_path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    m = PATTERN.search(text.split('===== attempt started')[-1])
    return m.group(0).strip() if m else None

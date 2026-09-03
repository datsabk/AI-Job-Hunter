"""AIJobHunter — a pluggable, multi-portal job discovery and application-draft tool.

The package is organised as a resumable pipeline of stages
(collect → parse → score → draft → export) backed by a small SQLite store, with
pluggable source adapters (where jobs come from) and apply adapters (how an
application is prepared). See the README for the full code tree.
"""

__version__ = "0.1.0"

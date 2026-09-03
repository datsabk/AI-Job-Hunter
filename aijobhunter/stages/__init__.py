"""Pipeline stages: collect, parse, score, draft, export.

Each stage is an independent function that reads rows from the store at its
input status, does its work, and advances them — so the pipeline is resumable
and any stage can be run on its own.
"""

# Schema

`factset.schema.json` is the contract between the analysis stage and
everything that reads its output: the writing stage, the verifier, the
Go miner and the web app.

It is generated from `core/src/plumb/model.py`. Do not edit it by hand.
After changing the models, run `uv run plumb schema` from `core`. CI fails
if the two drift apart.

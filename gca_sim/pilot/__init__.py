"""Controlled agent pilot (E5): shared against isolated notes on matched quotation tasks.

The design is fixed in experiments/agent_pilot_plan.md. This package holds the task bank generator, the prompt
and notes store, the scorer, the spending guard, the model client and the runner. Nothing here calls a paid
model unless a model, its prices and a spending cap are set in experiments/agent_pilot/config.yaml.
"""

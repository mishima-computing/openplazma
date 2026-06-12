# Worktree Policy

## Purpose

This policy prevents multiple writers from sharing the same writable target.

## Read-only Agents

Read-only agents may run in the main checkout:

- aggressive-designer
- conservative-designer
- genius
- aufheben-designer

## Workflow-only Writers

These agents may write only under `.github/workflows/**`:

- functional-ci-action-writer
- security-ci-action-writer
- nonfunctional-ci-action-writer

They must not edit application code, tests, package manifests, lockfiles, secrets, deployments, or branch protection.

## Contract-bound Writer

`implementer` may write only files allowed by the implementation contract.

It must not edit `.github/workflows/**`, bootstrap pack files, agent role specs, bootstrap schemas, or `Legacy/**` unless the implementation contract explicitly allows it.

## Ownership Rule

One active writer owns one branch or worktree.

Two active writers must not share:

- a branch
- a worktree
- a patch application target

## SHA Rule

Before write work, record:

- run_id
- agent
- target branch
- locked_target_sha

Before final reporting, reread HEAD as current_target_sha.

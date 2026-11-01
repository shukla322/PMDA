"""CLI for reviewing campaign state and deterministic chemistry evidence."""

import argparse
import json
from pathlib import Path

from .store import Store
from .execution import ExecutionService


def _main():
    parser = argparse.ArgumentParser(prog="pmda")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2] / "runtime/campaigns"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    create = commands.add_parser("create")
    create.add_argument("objective")
    for name in ("show", "ledger", "history", "audit", "archive"):
        commands.add_parser(name).add_argument("campaign")
    transition = commands.add_parser("transition")
    transition.add_argument("campaign")
    transition.add_argument("state")
    transition.add_argument("--revision", type=int, required=True)
    approve = commands.add_parser("approve")
    approve.add_argument("campaign")
    approve.add_argument("artifact")
    approve.add_argument("--sha256", required=True)
    approve.add_argument("--actor", required=True)
    approve.add_argument("--role", choices=["scientist","operator"])
    approve.add_argument("--comments",default="")
    revise = commands.add_parser("revise")
    revise.add_argument("campaign")
    revise.add_argument("reason")
    launch = commands.add_parser("launch")
    launch.add_argument("campaign")
    launch.add_argument("approval")
    for name in ("job", "recover", "cancel", "abandon"):
        commands.add_parser(name).add_argument("job")
    args = parser.parse_args()
    store = Store(args.root)
    if args.command == "list":
        result = store.list_campaigns()
    elif args.command == "archive":
        store.archive(args.campaign)
        result = store.snapshot(args.campaign)
    elif args.command == "create":
        result = store.create(args.objective)
    elif args.command == "show":
        result = store.snapshot(args.campaign)
    elif args.command == "history":
        result = store.history(args.campaign)
    elif args.command == "ledger":
        result = str(store.render(args.campaign))
    elif args.command == "transition":
        store.transition(args.campaign, args.state, args.revision)
        result = store.get(args.campaign)
    elif args.command == "audit":
        result = {"event_chain_head": store.verify_history(args.campaign)}
    elif args.command == "revise":
        store.request_revision(args.campaign,args.reason)
        result = store.get(args.campaign)
    elif args.command == "launch":
        result = ExecutionService(store).launch(args.campaign,args.approval)
    elif args.command in {"job","recover","cancel","abandon"}:
        service=ExecutionService(store)
        method=service.cancel if args.command=="cancel" else service.abandon_orphan if args.command=="abandon" else service.reconcile
        result=method(args.job)
    else:
        result = store.approve(args.campaign, args.artifact, args.sha256, args.actor,args.role,args.comments)
    print(json.dumps(result, indent=2))


def main():
    from .contracts import PolicyError
    try:
        _main()
    except (PolicyError,ValueError,FileNotFoundError) as exc:
        code="POLICY_VIOLATION" if isinstance(exc,PolicyError) else "MISSING_ARTIFACT" if isinstance(exc,FileNotFoundError) else "INVALID_INPUT"
        print(json.dumps({"status":"error","error_code":code,"message":str(exc)}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()

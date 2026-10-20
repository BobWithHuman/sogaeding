"""Explicit receipt-only reconciliation. This utility never invokes the executor."""
import argparse
import asyncio
import os
from uuid import UUID

from app.common import SafeError
from app.executor.demo import DemoExecutor
from app.gateway.client import ControlClient


async def reconcile(cid, reservation):
    receipt = DemoExecutor(os.environ["EFFECTS_DB_PATH"]).receipt(cid)
    if receipt is None:
        raise SafeError("EXECUTION_OUTCOME_UNKNOWN")
    result = await ControlClient().post(f"/internal/calls/{cid}/report", {
        "reservation_id": reservation, "state": "SUCCEEDED", "receipt": receipt,
        "reconciled": True}, "ExecutionView")
    print(f"Reconciled {cid}: {result['state']}; no executor execution attempted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("call_id", type=UUID)
    parser.add_argument("reservation_id", type=UUID)
    args = parser.parse_args()
    try:
        asyncio.run(reconcile(str(args.call_id), str(args.reservation_id)))
    except SafeError as exc:
        parser.exit(1, exc.code + "\n")

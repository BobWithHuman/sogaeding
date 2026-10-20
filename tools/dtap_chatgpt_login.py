"""Dedicated login helper: interactive OAuth and model catalog only, no inference."""

import argparse
from pathlib import Path

from app.benchmark.siwc_auth import Credentials
from app.common import canonical


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["login", "account-check", "logout"])
    p.add_argument("--account", default="main")
    args = p.parse_args()
    credentials = Credentials(Path("/credentials"), args.account)
    if args.mode == "login":
        result = credentials.sign_in()
    elif args.mode == "account-check":
        result = credentials.models()
    else:
        result = credentials.revoke()
    print(canonical(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never print provider bodies, JWTs, callback URLs or exception locals.
        from app.benchmark.runtime_budget import StopRun

        print(
            canonical(
                {
                    "state": "STOPPED",
                    "code": str(error)
                    if isinstance(error, StopRun)
                    else "SIWC_VALIDATION_OR_TRANSPORT_REJECTED",
                    "inference": "NOT_RUN",
                    "api_key_fallback": False,
                }
            )
        )
        raise SystemExit(2) from None

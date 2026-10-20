"""Check the pre-implementation contract gate, without claiming app behavior."""

from tools.check_contracts import check_contracts


def test_checked_in_contract_examples() -> None:
    assert check_contracts() > 0

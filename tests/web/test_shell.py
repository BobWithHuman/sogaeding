from pathlib import Path


def test_external_values_use_text_nodes_and_no_persistent_credentials():
    root = Path("/workspace/src/app/web")
    script = (root / "ui.js").read_text()
    assert ".textContent" in script
    assert "innerHTML" not in script and "localStorage" not in script and "document.cookie" not in script
    assert "expected_args_sha256" in script and "exact_action" in script
    html = (root / "index.html").read_text()
    assert 'type="password"' in html and 'src="/ui.js"' in html

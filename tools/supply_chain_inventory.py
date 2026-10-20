"""Installed metadata and license gaps, without treating metadata as legal clearance."""
import importlib.metadata
import json
import platform
import sys
from datetime import UTC, datetime

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def main():
    installed = {canonicalize_name(d.metadata["Name"]): d for d in importlib.metadata.distributions()}
    components = []
    for name, dist in sorted(installed.items()):
        metadata = dist.metadata
        dependencies = []
        unknown = []
        for raw in dist.requires or []:
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            dep = canonicalize_name(requirement.name)
            (dependencies if dep in installed else unknown).append(dep)
        components.append({"name": name, "version": dist.version,
            "purl": f"pkg:pypi/{name}@{dist.version}",
            "supplier": metadata.get("Author-email") or metadata.get("Author") or "UNKNOWN",
            "license_expression": metadata.get("License-Expression"), "license": metadata.get("License"),
            "license_classifiers": [x for x in metadata.get_all("Classifier", []) if x.startswith("License ::")],
            "requires": dependencies, "missing_dependencies": unknown,
            "location": str(dist.locate_file(""))})
    value = {"created_at": datetime.now(UTC).isoformat(), "python": platform.python_version(),
             "author": "WP-MVP-01 implementation integrator", "components": components,
             "scope": "installed development/product image; OS tracked separately",
             "limitations": ["metadata does not establish distribution compliance", "OS CVE scan NOT_RUN",
                              "supplier/attribution completeness requires review"]}
    json.dump(value, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

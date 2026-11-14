import hashlib
from pathlib import Path

import ijson


def records(path: Path):
    with path.open("rb") as stream:
        yield from ijson.items(stream, "vulnerabilities.item", use_float=True)


def inventory(root: Path):
    result = []
    for path in sorted(root.rglob("nvdcve-2.0-*.json")):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        count = sum(1 for _ in records(path))
        with path.open("rb") as stream:
            metadata = {}
            for prefix, event, value in ijson.parse(stream):
                if prefix == "vulnerabilities":
                    break
                if event in ("string", "number") and "." not in prefix:
                    metadata[prefix] = value
        result.append(
            {
                "path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
                "count": count,
                "metadata": metadata,
            }
        )
    if not result:
        raise FileNotFoundError(f"No NVD feeds under {root}")
    return result

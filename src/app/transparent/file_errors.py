"""A closed typed business error; transported through the authenticated upstream.

An arbitrary MCP error or text claiming this shape is not a completion receipt.
Only the actual upstream READ open failure creates this exact result envelope.
"""
MESSAGE = "The requested registered file does not exist. No file was written."


def missing_read_result():
    return {"content": [{"type": "text", "text": MESSAGE}], "isError": True,
            "structuredContent": {"with_human_error": {"version": "file-error-1", "code": "FILE_NOT_FOUND",
                                                      "operation": "READ", "effect": "NO_WRITE"}}}


def valid_read_error(result):
    return type(result) is dict and type(result.get("isError")) is bool and result == missing_read_result()

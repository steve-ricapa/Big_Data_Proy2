"""Explicit additive output contracts and strict, value-redacting SDK tools."""
import json
import re
from typing import Annotated, Literal, NotRequired

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.tools.base import Tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BeforeValidator, ConfigDict, Field, ValidationError, WithJsonSchema
from typing_extensions import TypedDict


def bounded_integer(maximum):
    patterns = {
        10000: r"^0*(?:[1-9][0-9]{0,3}|10000)$",
        100: r"^0*(?:[1-9][0-9]?|100)$",
        250: r"^0*(?:[1-9][0-9]?|1[0-9]{2}|2[0-4][0-9]|250)$",
    }
    pattern = patterns[maximum]

    def parse(value):
        if isinstance(value, str) and len(value) <= 16 and re.fullmatch(pattern, value):
            return int(value)
        if type(value) is not int:
            raise ValueError("Expected a bounded integer or ASCII digit string")
        return value

    return Annotated[int, Field(ge=1, le=maximum, strict=True), BeforeValidator(parse), WithJsonSchema({
        "anyOf": [{"type": "integer", "minimum": 1, "maximum": maximum},
                  {"type": "string", "pattern": pattern, "maxLength": 16}],
        "description": "Integer or bounded ASCII digit string (compatibility coercion); boolean/floating input is rejected.",
    })]


class CVSSRecord(TypedDict):
    version: str
    score: float
    severity: str
    vector: str | None
    source: str | None


class CVERecord(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    cve_id: str
    description: NotRequired[str]
    severity: NotRequired[str]
    cvss: NotRequired[CVSSRecord | None]
    raw_cve: NotRequired[dict]
    products: NotRequired[list[dict]]
    cpes: NotRequired[list[dict]]
    applicability: NotRequired[dict]
    metadata: NotRequired[dict]


class SearchResponse(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    items: list[CVERecord]
    total: int
    page: int
    page_size: int
    metadata: NotRequired[dict]


class ProductItem(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    id: str
    part: str
    vendor: str
    product: str
    cve_count: NotRequired[int]


class CPEItem(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    criteria: str
    product_id: str
    constraints: NotRequired[list[dict]]
    identity_is_not_version_assertion: NotRequired[bool]


class ProductsResponse(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    items: list[ProductItem | tuple[str, int]]
    cve_id: NotRequired[str]
    cpes: NotRequired[list[CPEItem]]
    mode: NotRequired[Literal["ranking", "catalog", "per_cve"]]
    total: NotRequired[int]
    page: NotRequired[int]
    page_size: NotRequired[int]
    metadata: NotRequired[dict]


class RankingResponse(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    items: list[tuple[str, int]]
    metadata: NotRequired[dict]


class StatisticsResponse(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    total_cves: int
    as_of: str
    severity: dict[str, int]
    rejected_cves: int
    metadata: NotRequired[dict]


class GraphResponse(TypedDict):
    __pydantic_config__ = ConfigDict(extra="allow")
    items: list[dict]
    limit: int
    total_relationships: int
    truncated: bool
    total: NotRequired[int]
    page: NotRequired[int]
    page_size: NotRequired[int]
    metadata: NotRequired[dict]


class StrictTool(Tool):
    async def run(self, arguments, context=None, convert_result=False):
        try:
            validated = self.fn_metadata.arg_model.model_validate(arguments)
        except ValidationError as error:
            # Never echo values supplied to invalid fields into logs/tool responses.
            fields = [".".join(str(p)[:64] for p in e["loc"]) + ":" + e["type"] for e in error.errors(include_input=False)[:20]]
            raise ToolError("Invalid arguments for " + self.name + ": " + ", ".join(fields)) from None
        result = await super().run(validated.model_dump_one_level(), context=context, convert_result=False)
        if not convert_result:
            return result
        try:
            output = self.fn_metadata.output_model.model_validate(result)
            payload = output.model_dump(mode="json", by_alias=True, exclude_unset=True)
        except ValidationError:
            raise ToolError("Response is incompatible with the published outputSchema") from None
        # Keep legacy JSON text, but avoid pretty-print inflation. Optional absent
        # fields must not be silently inserted as null only in structuredContent.
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
            structuredContent=payload,
        )


def registered_tool(function):
    tool = StrictTool.from_function(
        function, structured_output=True,
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False),
    )
    original = tool.fn_metadata.arg_model
    strict = type("Strict" + original.__name__, (original,), {"model_config": ConfigDict(extra="forbid", arbitrary_types_allowed=True)})
    tool.fn_metadata.arg_model = strict
    tool.parameters = strict.model_json_schema(by_alias=True)
    # SDK1.30 converts a top-level TypedDict to a default extra=ignore model.
    # Preserve legacy fields that are intentionally additive, never strip them.
    original_output = tool.fn_metadata.output_model
    output = type("Additive" + original_output.__name__, (original_output,), {"model_config": ConfigDict(extra="allow")})
    tool.fn_metadata.output_model = output
    tool.fn_metadata.output_schema = output.model_json_schema()
    return tool

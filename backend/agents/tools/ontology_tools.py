"""Ontology management tools — voice-controlled editing of the knowledge
graph schema (OWL ontology as agent-friendly JSON).

Each function is registered as an ADK tool on the OntologyAgent sub-agent.
Docstrings serve as the tool descriptions visible to the LLM.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agents import context as ctx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory ontology store (used when OntologyManager is not available)
# ---------------------------------------------------------------------------

_DEFAULT_ONTOLOGY: dict[str, Any] = {
    "metadata": {
        "name": "VoiceGraph Domain Ontology",
        "namespace": "http://voicegraph.ai/ontology/",
        "version": "1.0",
        "modified": datetime.now(timezone.utc).isoformat(),
    },
    "classes": {
        "Thing": {
            "uri": "http://voicegraph.ai/ontology/Thing",
            "label": "Thing",
            "subClassOf": None,
            "description": "Root class for all entities",
        },
    },
    "objectProperties": {},
    "datatypeProperties": {},
}

_local_ontology: dict[str, Any] | None = None


def _get_store() -> dict[str, Any]:
    """Return the ontology dict — from OntologyManager if available,
    else from the local in-memory store."""
    global _local_ontology

    mgr = ctx.ontology_manager
    if mgr is not None:
        try:
            return mgr.to_json()
        except Exception:  # noqa: BLE001
            pass

    if _local_ontology is None:
        _local_ontology = _DEFAULT_ONTOLOGY.copy()
    return _local_ontology


def _save(ontology: dict[str, Any]) -> None:
    """Persist ontology changes."""
    global _local_ontology

    ontology["metadata"]["modified"] = datetime.now(timezone.utc).isoformat()

    mgr = ctx.ontology_manager
    if mgr is not None:
        try:
            mgr.from_json(ontology)
            mgr.save()
            return
        except Exception:  # noqa: BLE001
            pass

    _local_ontology = ontology


# ---------------------------------------------------------------------------
# Tool: get_ontology
# ---------------------------------------------------------------------------


def get_ontology() -> dict:
    """Get the current ontology as JSON with all classes, object properties,
    and datatype properties. Call this first to see the current schema
    before making changes."""

    ont = _get_store()
    return {
        "ontology": ont,
        "class_count": len(ont.get("classes", {})),
        "property_count": len(ont.get("objectProperties", {})),
        "message": "Current ontology loaded.",
    }


# ---------------------------------------------------------------------------
# Tool: add_class
# ---------------------------------------------------------------------------


def add_class(class_name: str, parent_class: str = "Thing", description: str = "") -> dict:
    """Add a new entity type (class) to the ontology.
    For example: add_class('Project', 'Thing', 'A planned undertaking')."""

    ont = _get_store()
    classes = ont.setdefault("classes", {})

    if class_name in classes:
        return {
            "success": False,
            "message": f"Class '{class_name}' already exists.",
        }

    if parent_class != "Thing" and parent_class not in classes:
        return {
            "success": False,
            "message": f"Parent class '{parent_class}' does not exist. Add it first or use 'Thing'.",
        }

    ns = ont["metadata"]["namespace"]
    classes[class_name] = {
        "uri": f"{ns}{class_name}",
        "label": class_name,
        "subClassOf": parent_class,
        "description": description,
    }
    _save(ont)

    return {
        "success": True,
        "class_name": class_name,
        "parent_class": parent_class,
        "message": f"Added class '{class_name}' under '{parent_class}'.",
    }


# ---------------------------------------------------------------------------
# Tool: remove_class
# ---------------------------------------------------------------------------


def remove_class(class_name: str) -> dict:
    """Remove an entity type (class) from the ontology.
    Warning: this also removes any properties that reference this class."""

    ont = _get_store()
    classes = ont.get("classes", {})

    if class_name not in classes:
        return {"success": False, "message": f"Class '{class_name}' not found."}

    if class_name == "Thing":
        return {"success": False, "message": "Cannot remove the root class 'Thing'."}

    # Check for child classes
    children = [c for c, info in classes.items()
                if info.get("subClassOf") == class_name]

    # Remove properties referencing this class
    obj_props = ont.get("objectProperties", {})
    removed_props = [
        p for p, info in obj_props.items()
        if info.get("domain") == class_name or info.get("range") == class_name
    ]
    for p in removed_props:
        del obj_props[p]

    # Reparent children to Thing
    for child in children:
        classes[child]["subClassOf"] = "Thing"

    del classes[class_name]
    _save(ont)

    return {
        "success": True,
        "class_name": class_name,
        "reparented_children": children,
        "removed_properties": removed_props,
        "message": f"Removed class '{class_name}'."
                   + (f" Reparented {children} to Thing." if children else "")
                   + (f" Removed properties: {removed_props}." if removed_props else ""),
    }


# ---------------------------------------------------------------------------
# Tool: add_object_property
# ---------------------------------------------------------------------------


def add_object_property(property_name: str, domain: str, range_class: str,
                        description: str = "") -> dict:
    """Add a new relationship type between two entity types.
    For example: add_object_property('worksAt', 'Person', 'Organization')."""

    ont = _get_store()
    classes = ont.get("classes", {})
    props = ont.setdefault("objectProperties", {})

    if property_name in props:
        return {"success": False, "message": f"Property '{property_name}' already exists."}

    for cls_name in (domain, range_class):
        if cls_name not in classes and cls_name != "Thing":
            return {
                "success": False,
                "message": f"Class '{cls_name}' not found in ontology. Add it first.",
            }

    ns = ont["metadata"]["namespace"]
    props[property_name] = {
        "uri": f"{ns}{property_name}",
        "label": property_name.replace("_", " "),
        "domain": domain,
        "range": range_class,
        "description": description,
    }
    _save(ont)

    return {
        "success": True,
        "property_name": property_name,
        "domain": domain,
        "range": range_class,
        "message": f"Added relationship type '{property_name}': {domain} -> {range_class}.",
    }


# ---------------------------------------------------------------------------
# Tool: remove_object_property
# ---------------------------------------------------------------------------


def remove_object_property(property_name: str) -> dict:
    """Remove a relationship type from the ontology."""

    ont = _get_store()
    props = ont.get("objectProperties", {})

    if property_name not in props:
        return {"success": False, "message": f"Property '{property_name}' not found."}

    del props[property_name]
    _save(ont)

    return {
        "success": True,
        "property_name": property_name,
        "message": f"Removed relationship type '{property_name}'.",
    }


# ---------------------------------------------------------------------------
# Tool: list_classes
# ---------------------------------------------------------------------------


def list_classes() -> dict:
    """List all entity types (classes) in the ontology with their hierarchy."""

    ont = _get_store()
    classes = ont.get("classes", {})

    hierarchy: list[dict] = []
    for name, info in classes.items():
        hierarchy.append({
            "name": name,
            "parent": info.get("subClassOf"),
            "description": info.get("description", ""),
        })

    return {
        "classes": hierarchy,
        "count": len(hierarchy),
        "message": f"Found {len(hierarchy)} entity types.",
    }


# ---------------------------------------------------------------------------
# Tool: list_properties
# ---------------------------------------------------------------------------


def list_properties(class_name: str = "") -> dict:
    """List all relationship types (object properties) in the ontology,
    optionally filtered to those involving a specific class."""

    ont = _get_store()
    props = ont.get("objectProperties", {})

    result: list[dict] = []
    for name, info in props.items():
        if class_name and class_name not in (info.get("domain"), info.get("range")):
            continue
        result.append({
            "name": name,
            "domain": info.get("domain", ""),
            "range": info.get("range", ""),
            "description": info.get("description", ""),
        })

    return {
        "properties": result,
        "count": len(result),
        "filter": class_name or "none",
        "message": f"Found {len(result)} relationship types"
                   + (f" involving '{class_name}'." if class_name else "."),
    }


# ---------------------------------------------------------------------------
# Tool: validate_ontology
# ---------------------------------------------------------------------------


def validate_ontology() -> dict:
    """Check the ontology for consistency issues such as orphaned references,
    circular hierarchies, or duplicate definitions."""

    ont = _get_store()
    classes = ont.get("classes", {})
    props = ont.get("objectProperties", {})
    issues: list[str] = []

    # Check parent references
    for name, info in classes.items():
        parent = info.get("subClassOf")
        if parent and parent != "Thing" and parent not in classes:
            issues.append(f"Class '{name}' references non-existent parent '{parent}'.")

    # Check property domain/range references
    for name, info in props.items():
        domain = info.get("domain", "")
        range_cls = info.get("range", "")
        if domain and domain not in classes and domain != "Thing":
            issues.append(f"Property '{name}' has unknown domain '{domain}'.")
        if range_cls and range_cls not in classes and range_cls != "Thing":
            issues.append(f"Property '{name}' has unknown range '{range_cls}'.")

    # Check for circular hierarchy (simple depth-limited check)
    for name in classes:
        visited: set[str] = set()
        current = name
        while current and current in classes:
            if current in visited:
                issues.append(f"Circular hierarchy detected involving '{name}'.")
                break
            visited.add(current)
            current = classes[current].get("subClassOf")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "classes_checked": len(classes),
        "properties_checked": len(props),
        "message": "Ontology is valid." if not issues else f"Found {len(issues)} issue(s).",
    }


# ---------------------------------------------------------------------------
# Tool: trigger_re_extraction
# ---------------------------------------------------------------------------


def trigger_re_extraction(scope: str = "new_types") -> dict:
    """Re-extract entities from documents after ontology changes.
    scope options:
      - 'new_types': only extract instances of newly added types
      - 'modified': re-extract types that were modified
      - 'full': complete re-extraction of all documents"""

    valid_scopes = ("new_types", "modified", "full")
    if scope not in valid_scopes:
        return {
            "success": False,
            "message": f"Invalid scope '{scope}'. Use one of: {valid_scopes}",
        }

    # TODO: Implement actual re-extraction pipeline
    # 1. Identify affected documents
    # 2. Re-run extraction with updated ontology
    # 3. Merge new entities into graph
    return {
        "success": True,
        "scope": scope,
        "message": f"Re-extraction triggered with scope '{scope}'. "
                   "This is a placeholder — extraction pipeline not yet connected.",
    }

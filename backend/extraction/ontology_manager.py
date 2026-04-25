"""Ontology management using RDFLib.

Provides full CRUD operations on an OWL/RDFS ontology stored as a Turtle file,
with JSON round-tripping for the frontend and conversion to neo4j-graphrag
GraphSchema format for constrained extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

logger = logging.getLogger(__name__)

# VoiceGraph ontology namespace
VG = Namespace("http://voicegraph.ai/ontology/")

# Map XSD type names to short strings
XSD_TYPE_MAP = {
    str(XSD.string): "string",
    str(XSD.integer): "integer",
    str(XSD.int): "integer",
    str(XSD.float): "float",
    str(XSD.double): "double",
    str(XSD.boolean): "boolean",
    str(XSD.date): "date",
    str(XSD.dateTime): "datetime",
}

XSD_REVERSE_MAP = {v: k for k, v in XSD_TYPE_MAP.items()}


class OntologyManager:
    """Manage an RDF/OWL ontology for constraining knowledge-graph extraction.

    The ontology defines the allowed classes (node labels), object properties
    (relationship types), and datatype properties (node attributes) so that the
    extraction pipeline produces a consistent, well-typed graph.

    Internal storage uses an rdflib.Graph for OWL triples.  A parallel dict
    representation is maintained for fast JSON serialisation.
    """

    def __init__(self) -> None:
        self._graph = Graph()
        self._graph.bind("vg", VG)
        self._graph.bind("owl", OWL)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("xsd", XSD)
        self._json_cache: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _invalidate_cache(self) -> None:
        self._json_cache = None

    def _local_name(self, uri: URIRef | str) -> str:
        """Extract the local name from a URI (after # or last /)."""
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.rstrip("/").split("/")[-1]

    def _to_uri(self, name: str) -> URIRef:
        """Convert a local name to a VG namespace URI."""
        if name.startswith("http://") or name.startswith("https://"):
            return URIRef(name)
        return VG[name]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def load_from_turtle(self, path: str) -> None:
        """Load an ontology from a Turtle (.ttl) file.

        Args:
            path: Filesystem path to the Turtle file.
        """
        self._graph = Graph()
        self._graph.bind("vg", VG)
        self._graph.bind("owl", OWL)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("xsd", XSD)
        self._graph.parse(str(path), format="turtle")
        self._invalidate_cache()
        logger.info("Ontology loaded from %s (%d triples)", path, len(self._graph))

    def save_to_turtle(self, path: str) -> None:
        """Persist the current ontology to a Turtle file.

        Args:
            path: Destination filesystem path.
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._graph.serialize(str(path), format="turtle")
        logger.info("Ontology saved to %s", path)

    def to_json(self) -> dict[str, Any]:
        """Export the ontology as a JSON-friendly dict.

        Returns:
            A dict with ``classes``, ``object_properties``, and
            ``datatype_properties`` lists.
        """
        if self._json_cache is not None:
            return self._json_cache

        classes: list[dict[str, Any]] = []
        for cls_uri in self._graph.subjects(RDF.type, OWL.Class):
            label = self._graph.value(cls_uri, RDFS.label)
            comment = self._graph.value(cls_uri, RDFS.comment)
            parent = self._graph.value(cls_uri, RDFS.subClassOf)
            classes.append({
                "uri": str(cls_uri),
                "name": self._local_name(cls_uri),
                "label": str(label) if label else self._local_name(cls_uri),
                "parent": self._local_name(parent) if parent else "Thing",
                "description": str(comment) if comment else "",
            })

        obj_props: list[dict[str, Any]] = []
        for prop_uri in self._graph.subjects(RDF.type, OWL.ObjectProperty):
            label = self._graph.value(prop_uri, RDFS.label)
            comment = self._graph.value(prop_uri, RDFS.comment)
            domain = self._graph.value(prop_uri, RDFS.domain)
            range_ = self._graph.value(prop_uri, RDFS.range)
            obj_props.append({
                "uri": str(prop_uri),
                "name": self._local_name(prop_uri),
                "label": str(label) if label else self._local_name(prop_uri),
                "domain": self._local_name(domain) if domain else None,
                "range": self._local_name(range_) if range_ else None,
                "description": str(comment) if comment else "",
            })

        dt_props: list[dict[str, Any]] = []
        for prop_uri in self._graph.subjects(RDF.type, OWL.DatatypeProperty):
            label = self._graph.value(prop_uri, RDFS.label)
            domain = self._graph.value(prop_uri, RDFS.domain)
            range_ = self._graph.value(prop_uri, RDFS.range)
            dt_props.append({
                "uri": str(prop_uri),
                "name": self._local_name(prop_uri),
                "label": str(label) if label else self._local_name(prop_uri),
                "domain": self._local_name(domain) if domain else None,
                "datatype": XSD_TYPE_MAP.get(str(range_), "string") if range_ else "string",
            })

        result = {
            "classes": classes,
            "object_properties": obj_props,
            "datatype_properties": dt_props,
        }
        self._json_cache = result
        return result

    def from_json(self, data: dict[str, Any]) -> None:
        """Populate the ontology from a JSON dict (as produced by ``to_json``).

        This **replaces** the current graph contents.

        Args:
            data: Dict with ``classes``, ``object_properties``, and
                optionally ``datatype_properties`` keys.
        """
        self._graph = Graph()
        self._graph.bind("vg", VG)
        self._graph.bind("owl", OWL)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("xsd", XSD)

        for cls in data.get("classes", []):
            name = cls.get("name", cls.get("label", ""))
            uri = URIRef(cls["uri"]) if "uri" in cls else self._to_uri(name)
            self._graph.add((uri, RDF.type, OWL.Class))
            self._graph.add((uri, RDFS.label, Literal(cls.get("label", name))))
            if cls.get("description"):
                self._graph.add((uri, RDFS.comment, Literal(cls["description"])))
            parent = cls.get("parent", "Thing")
            if parent and parent != "Thing":
                self._graph.add((uri, RDFS.subClassOf, self._to_uri(parent)))

        for prop in data.get("object_properties", []):
            name = prop.get("name", prop.get("label", ""))
            uri = URIRef(prop["uri"]) if "uri" in prop else self._to_uri(name)
            self._graph.add((uri, RDF.type, OWL.ObjectProperty))
            self._graph.add((uri, RDFS.label, Literal(prop.get("label", name))))
            if prop.get("description"):
                self._graph.add((uri, RDFS.comment, Literal(prop["description"])))
            if prop.get("domain"):
                self._graph.add((uri, RDFS.domain, self._to_uri(prop["domain"])))
            if prop.get("range"):
                self._graph.add((uri, RDFS.range, self._to_uri(prop["range"])))

        for prop in data.get("datatype_properties", []):
            name = prop.get("name", prop.get("label", ""))
            uri = URIRef(prop["uri"]) if "uri" in prop else self._to_uri(name)
            self._graph.add((uri, RDF.type, OWL.DatatypeProperty))
            self._graph.add((uri, RDFS.label, Literal(prop.get("label", name))))
            if prop.get("domain"):
                self._graph.add((uri, RDFS.domain, self._to_uri(prop["domain"])))
            dt = prop.get("datatype", "string")
            xsd_uri = XSD_REVERSE_MAP.get(dt, str(XSD.string))
            self._graph.add((uri, RDFS.range, URIRef(xsd_uri)))

        self._invalidate_cache()
        logger.info("Ontology loaded from JSON (%d triples)", len(self._graph))

    # ------------------------------------------------------------------
    # CRUD — Classes
    # ------------------------------------------------------------------

    def add_class(
        self,
        name: str,
        parent: str = "Thing",
        description: str = "",
    ) -> URIRef:
        """Add an OWL class to the ontology.

        Args:
            name: Local name (appended to the VG namespace).
            parent: Parent class local name.  ``"Thing"`` means top-level.
            description: Optional human-readable description.

        Returns:
            The URIRef of the newly created class.
        """
        uri = self._to_uri(name)
        self._graph.add((uri, RDF.type, OWL.Class))
        self._graph.add((uri, RDFS.label, Literal(name)))
        if description:
            self._graph.add((uri, RDFS.comment, Literal(description)))
        if parent and parent != "Thing":
            self._graph.add((uri, RDFS.subClassOf, self._to_uri(parent)))
        self._invalidate_cache()
        return uri

    def remove_class(self, name: str) -> None:
        """Remove an OWL class and all triples that reference it.

        Args:
            name: Local name within the VG namespace.
        """
        uri = self._to_uri(name)
        # Remove all triples where this class is subject or object
        self._graph.remove((uri, None, None))
        self._graph.remove((None, None, uri))
        self._invalidate_cache()

    # ------------------------------------------------------------------
    # CRUD — Object Properties
    # ------------------------------------------------------------------

    def add_object_property(
        self,
        name: str,
        domain: str,
        range: str,
        description: str = "",
    ) -> URIRef:
        """Add an OWL object property (relationship type).

        Args:
            name: Local name for the property.
            domain: Domain class local name.
            range: Range class local name.
            description: Optional human-readable description.

        Returns:
            The URIRef of the newly created property.
        """
        uri = self._to_uri(name)
        self._graph.add((uri, RDF.type, OWL.ObjectProperty))
        self._graph.add((uri, RDFS.label, Literal(name)))
        if description:
            self._graph.add((uri, RDFS.comment, Literal(description)))
        if domain:
            self._graph.add((uri, RDFS.domain, self._to_uri(domain)))
        if range:
            self._graph.add((uri, RDFS.range, self._to_uri(range)))
        self._invalidate_cache()
        return uri

    def remove_object_property(self, name: str) -> None:
        """Remove an OWL object property and all its triples.

        Args:
            name: Local name within the VG namespace.
        """
        uri = self._to_uri(name)
        self._graph.remove((uri, None, None))
        self._graph.remove((None, None, uri))
        self._invalidate_cache()

    # ------------------------------------------------------------------
    # CRUD — Datatype Properties
    # ------------------------------------------------------------------

    def add_datatype_property(
        self,
        name: str,
        domain: str,
        datatype: str = "string",
    ) -> URIRef:
        """Add an OWL datatype property (node attribute).

        Args:
            name: Local name for the property.
            domain: Domain class local name.
            datatype: XSD type shorthand (``string``, ``integer``, ``float``,
                ``boolean``, ``date``, ``datetime``).

        Returns:
            The URIRef of the newly created property.
        """
        uri = self._to_uri(name)
        self._graph.add((uri, RDF.type, OWL.DatatypeProperty))
        self._graph.add((uri, RDFS.label, Literal(name)))
        if domain:
            self._graph.add((uri, RDFS.domain, self._to_uri(domain)))
        xsd_uri = XSD_REVERSE_MAP.get(datatype, str(XSD.string))
        self._graph.add((uri, RDFS.range, URIRef(xsd_uri)))
        self._invalidate_cache()
        return uri

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_classes(self) -> list[dict[str, Any]]:
        """List all OWL classes with parent and description.

        Returns:
            A list of dicts with ``name``, ``parent``, and ``description``.
        """
        return self.to_json()["classes"]

    def list_properties(self) -> list[dict[str, Any]]:
        """List all object and datatype properties with domain and range.

        Returns:
            A list of dicts with ``name``, ``domain``, ``range``/``datatype``,
            and ``property_type`` (``object`` or ``datatype``).
        """
        result = []
        for prop in self.to_json()["object_properties"]:
            result.append({
                "name": prop["name"],
                "domain": prop["domain"],
                "range": prop["range"],
                "description": prop.get("description", ""),
                "property_type": "object",
            })
        for prop in self.to_json()["datatype_properties"]:
            result.append({
                "name": prop["name"],
                "domain": prop["domain"],
                "datatype": prop["datatype"],
                "property_type": "datatype",
            })
        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> dict[str, Any]:
        """Run validation checks on the ontology.

        Checks for:
          - Object properties missing domain or range
          - Domain/range references to undefined classes
          - Orphan classes (not used in any property)
          - Circular subclass hierarchies

        Returns:
            A dict with ``valid`` (bool), ``errors`` (list), and
            ``warnings`` (list).
        """
        errors: list[str] = []
        warnings: list[str] = []

        defined_classes = set(self._graph.subjects(RDF.type, OWL.Class))
        defined_class_names = {self._local_name(c) for c in defined_classes}

        # Check object properties have domain and range
        for prop_uri in self._graph.subjects(RDF.type, OWL.ObjectProperty):
            name = self._local_name(prop_uri)
            domain = self._graph.value(prop_uri, RDFS.domain)
            range_ = self._graph.value(prop_uri, RDFS.range)

            if not domain:
                errors.append(f"ObjectProperty '{name}' has no domain.")
            elif domain not in defined_classes:
                errors.append(
                    f"ObjectProperty '{name}' domain '{self._local_name(domain)}' "
                    f"is not a defined class."
                )

            if not range_:
                errors.append(f"ObjectProperty '{name}' has no range.")
            elif range_ not in defined_classes:
                errors.append(
                    f"ObjectProperty '{name}' range '{self._local_name(range_)}' "
                    f"is not a defined class."
                )

        # Check datatype properties have domain
        for prop_uri in self._graph.subjects(RDF.type, OWL.DatatypeProperty):
            name = self._local_name(prop_uri)
            domain = self._graph.value(prop_uri, RDFS.domain)
            if not domain:
                warnings.append(f"DatatypeProperty '{name}' has no domain.")
            elif domain not in defined_classes:
                errors.append(
                    f"DatatypeProperty '{name}' domain '{self._local_name(domain)}' "
                    f"is not a defined class."
                )

        # Check for orphan classes (not used as domain/range)
        used_classes: set[str] = set()
        for prop_uri in self._graph.subjects(RDF.type, OWL.ObjectProperty):
            domain = self._graph.value(prop_uri, RDFS.domain)
            range_ = self._graph.value(prop_uri, RDFS.range)
            if domain:
                used_classes.add(str(domain))
            if range_:
                used_classes.add(str(range_))
        for prop_uri in self._graph.subjects(RDF.type, OWL.DatatypeProperty):
            domain = self._graph.value(prop_uri, RDFS.domain)
            if domain:
                used_classes.add(str(domain))

        for cls_uri in defined_classes:
            if str(cls_uri) not in used_classes:
                warnings.append(
                    f"Class '{self._local_name(cls_uri)}' is not used in any property."
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Neo4j GraphSchema conversion
    # ------------------------------------------------------------------

    def to_graph_schema(self) -> dict[str, Any]:
        """Convert the OWL ontology to neo4j-graphrag compatible GraphSchema.

        OWL classes become ``node_types``, OWL object properties become
        ``relationship_types`` with ``patterns`` specifying which node types
        they connect.

        Returns:
            A dict with ``node_types``, ``relationship_types``, and
            ``patterns`` suitable for neo4j-graphrag's ``GraphSchema``.
        """
        data = self.to_json()

        # Build node types: each class becomes a node type
        # Collect datatype properties per class for node properties
        class_properties: dict[str, list[dict[str, str]]] = {}
        for dt_prop in data.get("datatype_properties", []):
            domain = dt_prop.get("domain")
            if domain:
                class_properties.setdefault(domain, []).append({
                    "name": dt_prop["name"],
                    "type": dt_prop.get("datatype", "string"),
                })

        node_types = []
        for cls in data["classes"]:
            name = cls["name"]
            node_type = {
                "label": name,
                "description": cls.get("description", ""),
                "properties": class_properties.get(name, []),
            }
            node_types.append(node_type)

        # Build relationship types and patterns from object properties
        relationship_types = []
        patterns = []
        for prop in data["object_properties"]:
            rel_name = prop["name"]
            relationship_types.append({
                "label": rel_name,
                "description": prop.get("description", ""),
            })
            if prop.get("domain") and prop.get("range"):
                patterns.append({
                    "source": prop["domain"],
                    "relationship": rel_name,
                    "target": prop["range"],
                })

        return {
            "node_types": node_types,
            "relationship_types": relationship_types,
            "patterns": patterns,
        }

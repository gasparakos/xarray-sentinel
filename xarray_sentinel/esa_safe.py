import functools
import os
import re
import typing as T
from xml.etree import ElementTree

import pkg_resources
import xmlschema

PathType = T.Union[str, "os.PathLike[str]"]
PathOrFileType = T.Union[PathType, T.TextIO]


SENTINEL1_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel-1.0",
    "s1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1",
    "s1sarl1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1/sar/level-1",
}

SENTINEL1_FOLDER = pkg_resources.resource_filename(__name__, "resources/sentinel1")
SENTINEL1_SCHEMAS = {
    "manifest": os.path.join(SENTINEL1_FOLDER, "my-xfdu.xsd"),
    "annotation": os.path.join(SENTINEL1_FOLDER, "s1-level-1-product.xsd"),
    "calibration": os.path.join(SENTINEL1_FOLDER, "s1-level-1-calibration.xsd"),
    "noise": os.path.join(SENTINEL1_FOLDER, "s1-level-1-noise.xsd"),
    "aux_orbit": os.path.join(SENTINEL1_FOLDER, "my-schema_orb.xsd"),
}

SENTINEL2_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel/1.1",
}


@functools.lru_cache
def cached_sentinel1_schemas(schema_type: str) -> xmlschema.XMLSchema:
    return xmlschema.XMLSchema(SENTINEL1_SCHEMAS[schema_type])


def parse_tag(
    xml_path: PathOrFileType,
    query: str,
    schema_type: str = "annotation",
    validation: str = "skip",
) -> T.Dict[str, T.Any]:
    schema = cached_sentinel1_schemas(schema_type)
    if hasattr(xml_path, "seek"):
        xml_path.seek(0)  # type: ignore
    xml_tree = ElementTree.parse(xml_path)
    tag_dict: T.Dict[str, T.Any] = schema.decode(xml_tree, query, validation=validation)  # type: ignore
    assert isinstance(tag_dict, dict), f"{type(tag_dict)} is not dict"
    return tag_dict


def parse_tag_as_list(
    xml_path: PathOrFileType,
    query: str,
    schema_type: str = "annotation",
    validation: str = "skip",
) -> T.List[T.Dict[str, T.Any]]:
    schema = cached_sentinel1_schemas(schema_type)
    xml_tree = ElementTree.parse(xml_path)
    tag: T.Union[None, list, dict] = schema.decode(xml_tree, query, validation=validation)  # type: ignore
    if tag is None:
        tag = []
    elif isinstance(tag, dict):
        tag = [tag]
    tag_list: T.List[T.Dict[str, T.Any]] = tag
    assert isinstance(tag_list, list), f"{type(tag_list)} is not list"
    return tag_list


def findtext(
    tree: ElementTree.ElementTree,
    query: str,
    namespaces: T.Dict[str, str] = SENTINEL1_NAMESPACES,
) -> str:
    value = tree.findtext(query, namespaces=namespaces)
    if value is None:
        raise ValueError(f"query={query} returned None")
    return value


def findall(
    tree: ElementTree.ElementTree,
    query: str,
    namespaces: T.Dict[str, str] = SENTINEL1_NAMESPACES,
) -> T.List[str]:
    tags = tree.findall(query, namespaces=namespaces)
    values: T.List[str] = []
    for tag in tags:
        if tag.text is None:
            raise ValueError(f"query={query} returned None")
        values.append(tag.text)
    return values


def parse_annotation_filename(name: str) -> T.Tuple[str, str, str, str]:
    match = re.match(
        r"([a-z-]*)s1[ab]-([^-]*)-[^-]*-([^-]*)-([\dt]*)-", os.path.basename(name)
    )
    if match is None:
        raise ValueError(f"cannot parse name {name!r}")
    return tuple(match.groups())  # type: ignore


@functools.lru_cache
def parse_manifest_sentinel1(
    manifest_path: PathOrFileType,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, T.Tuple[str, str, str, str, str]]]:
    # We use ElementTree because we didn't find a XSD definition for the manifest
    manifest = ElementTree.parse(manifest_path)

    family_name = findtext(manifest, ".//safe:platform/safe:familyName")
    if family_name != "SENTINEL-1":
        raise ValueError(f"familyName={family_name} not supported")

    number = findtext(manifest, ".//safe:platform/safe:number")
    mode = findtext(manifest, ".//s1sarl1:instrumentMode/s1sarl1:mode")
    swaths = findall(manifest, ".//s1sarl1:instrumentMode/s1sarl1:swath")

    orbit_number = findall(manifest, ".//safe:orbitNumber")
    if len(orbit_number) != 2 or orbit_number[0] != orbit_number[1]:
        raise ValueError(f"orbitNumber={orbit_number} not supported")

    relative_orbit_number = findall(manifest, ".//safe:relativeOrbitNumber")
    if (
        len(relative_orbit_number) != 2
        or relative_orbit_number[0] != relative_orbit_number[1]
    ):
        raise ValueError(f"relativeOrbitNumber={relative_orbit_number} not supported")

    orbit_pass = findtext(manifest, ".//s1:pass")
    if orbit_pass not in {"ASCENDING", "DESCENDING"}:
        raise ValueError(f"pass={orbit_pass} not supported")

    ascending_node_time = findtext(manifest, ".//s1:ascendingNodeTime")

    transmitter_receiver_polarisations = findall(
        manifest, ".//s1sarl1:transmitterReceiverPolarisation"
    )
    product_type = findtext(manifest, ".//s1sarl1:productType")

    start_time = findtext(manifest, ".//safe:startTime")
    stop_time = findtext(manifest, ".//safe:stopTime")

    attributes = {
        "family_name": family_name,
        "number": number,
        "mode": mode,
        "swaths": swaths,
        "orbit_number": int(orbit_number[0]),
        "relative_orbit_number": int(relative_orbit_number[0]),
        "pass": orbit_pass,
        "ascending_node_time": ascending_node_time,
        "transmitter_receiver_polarisations": transmitter_receiver_polarisations,
        "product_type": product_type,
        "start_time": start_time,
        "stop_time": stop_time,
    }

    files = {}

    for file_tag in manifest.findall(".//dataObjectSection/dataObject"):
        location_tag = file_tag.find(".//fileLocation")
        if location_tag is not None:
            file_href = location_tag.attrib["href"]
            try:
                description = parse_annotation_filename(os.path.basename(file_href))
            except ValueError:
                continue
            file_type = file_tag.attrib["repID"]
            files[file_href] = (file_type,) + description

    return attributes, files

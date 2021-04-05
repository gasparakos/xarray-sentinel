import os
import pathlib
import typing as T
from xml.etree import ElementTree

SENTINEL1_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel-1.0",
    "s1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1",
    "s1sarl1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1/sar/level-1",
}

SENTINEL2_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel/1.1",
}


def open_manifest(
    product_folder: T.Union[str, "os.PathLike[str]"]
) -> ElementTree.ElementTree:
    product_folder = pathlib.Path(product_folder)
    return ElementTree.parse(product_folder / "manifest.safe")


def parse_manifest_sentinel1(
    manifest: ElementTree.ElementTree,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    familyName = manifest.findtext(
        ".//safe:platform/safe:familyName", namespaces=SENTINEL1_NAMESPACES
    )
    if familyName != "SENTINEL-1":
        raise ValueError(f"{familyName=} not supported")

    number = manifest.findtext(
        ".//safe:platform/safe:number", namespaces=SENTINEL1_NAMESPACES
    )
    if number is None:
        raise ValueError(f"{number=} not supported")

    instrumentMode = manifest.findtext(
        ".//s1sarl1:instrumentMode/s1sarl1:mode", namespaces=SENTINEL1_NAMESPACES
    )

    swaths = manifest.findall(
        ".//s1sarl1:instrumentMode/s1sarl1:swath", namespaces=SENTINEL1_NAMESPACES
    )

    transmitterReceiverPolarisation = manifest.findall(
        ".//s1sarl1:transmitterReceiverPolarisation", namespaces=SENTINEL1_NAMESPACES
    )

    productType = manifest.findtext(
        ".//s1sarl1:standAloneProductInformation/s1sarl1:productType",
        namespaces=SENTINEL1_NAMESPACES,
    )

    orbitProperties_pass = manifest.findtext(
        ".//s1:orbitProperties/s1:pass", namespaces=SENTINEL1_NAMESPACES
    )
    if orbitProperties_pass not in {"ASCENDING", "DESCENDING"}:
        raise ValueError(f"{orbitProperties_pass=} not supported")

    ascendingNodeTime = manifest.findtext(
        ".//s1:orbitProperties/s1:ascendingNodeTime", namespaces=SENTINEL1_NAMESPACES
    )
    if ascendingNodeTime is None:
        raise ValueError(f"{ascendingNodeTime=} not supported")

    orbitNumber = manifest.findall(
        ".//safe:orbitReference/safe:orbitNumber", namespaces=SENTINEL1_NAMESPACES
    )
    if (
        len(orbitNumber) != 2
        or orbitNumber[0].text != orbitNumber[1].text
        or orbitNumber[0].text is None
    ):
        raise ValueError(f"orbitNumber={[o.text for o in orbitNumber]} not supported")

    relativeOrbitNumber = manifest.findall(
        ".//safe:orbitReference/safe:relativeOrbitNumber",
        namespaces=SENTINEL1_NAMESPACES,
    )
    if (
        len(relativeOrbitNumber) != 2
        or relativeOrbitNumber[0].text != relativeOrbitNumber[1].text
        or relativeOrbitNumber[0].text is None
    ):
        raise ValueError(
            f"relativeOrbitNumber={[o.text for o in relativeOrbitNumber]} not supported"
        )

    attributes = {
        "constellation": "sentinel-1",
        "platform": "sentinel-1" + number.lower(),
        "instrument": ["c-sar"],
        "sat:orbit_state": orbitProperties_pass.lower(),
        "sat:absolute_orbit": int(orbitNumber[0].text),
        "sat:relative_orbit": int(relativeOrbitNumber[0].text),
        "sat:anx_datetime": ascendingNodeTime + "Z",
        "sar:frequency_band": "C",
        "sar:instrument_mode": instrumentMode,
        "sar:polarizations": [p.text for p in transmitterReceiverPolarisation],
        "sar:product_type": productType,
        "xs:instrument_mode_swaths": [s.text for s in swaths],
    }

    files = {}

    for file_tag in manifest.findall(".//dataObjectSection/dataObject"):
        file_href = file_tag.find(".//fileLocation").attrib["href"]
        file_type = file_tag.attrib["repID"]
        files[file_href] = file_type

    return attributes, files


def parse_manifest_sentinel2(
    manifest: ElementTree.ElementTree,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    familyName = manifest.findtext(
        ".//safe:platform/safe:familyName", namespaces=SENTINEL2_NAMESPACES
    )
    if familyName != "SENTINEL":
        raise ValueError(f"{familyName=} not supported")

    number = manifest.findtext(
        ".//safe:platform/safe:number", namespaces=SENTINEL2_NAMESPACES
    )
    if number is None:
        raise ValueError(f"{number=} not supported")

    groundTrackDirection = manifest.find(
        ".//safe:orbitReference/safe:orbitNumber", namespaces=SENTINEL2_NAMESPACES
    ).attrib["groundTrackDirection"]
    if groundTrackDirection not in {"ascending", "descending"}:
        raise ValueError(f"{groundTrackDirection=} not supported")

    orbitNumber = manifest.findtext(
        ".//safe:orbitReference/safe:orbitNumber", namespaces=SENTINEL2_NAMESPACES
    )

    relativeOrbitNumber = manifest.findtext(
        ".//safe:orbitReference/safe:relativeOrbitNumber",
        namespaces=SENTINEL2_NAMESPACES,
    )

    mtd_product_type = manifest.find(
        ".//dataObject[@ID='S2_Level-1C_Product_Metadata']/byteStream/fileLocation",
        namespaces=SENTINEL2_NAMESPACES,
    ).attrib["href"]
    if "MTD_MSIL1C.xml" in mtd_product_type:
        product_type = "S2MSIl1C"
    else:
        raise ValueError(f"{mtd_product_type=} not suppoorted")

    attributes = {
        "constellation": "sentinel-2",
        "platform": "sentinel-" + number.lower(),
        "instrument": ["msi"],
        "sat:orbit_state": groundTrackDirection.lower(),
        "sat:absolute_orbit": int(orbitNumber),
        "sat:relative_orbit": int(relativeOrbitNumber),
        "xs:product_type": product_type,
    }

    files = {}

    for file_tag in manifest.findall(".//dataObjectSection/dataObject"):
        file_href = file_tag.find(".//fileLocation").attrib["href"]
        file_type = file_tag.attrib["ID"]
        files[file_href] = file_type

    return attributes, files

import pathlib

import fsspec  # type: ignore
import numpy as np
import pytest
import xarray as xr

from xarray_sentinel import sentinel1

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)
SLC_IW1_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_calibration = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "annotation"
    / "calibration"
    / "calibration-s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_IW1_VV_measurement = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
    / "measurement"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.tiff"
)
SLC_S3_VV_annotation = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
    / "annotation"
    / "s1a-s3-slc-vv-20210401t152855-20210401t152914-037258-04638e-002.xml"
)
SLC_S3_VV_measurement = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
    / "measurement"
    / "s1a-s3-slc-vv-20210401t152855-20210401t152914-037258-04638e-002.tiff"
)
GRD_IW_VV_annotation = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
    / "annotation"
    / "s1b-iw-grd-vv-20210401t052623-20210401t052648-026269-032297-001.xml"
)


def test_open_dataset_zip() -> None:
    zip_path = (
        DATA_FOLDER
        / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.zip"
    )
    zip_urlpath = f"zip://*/manifest.safe::{zip_path}"
    expected_groups = {
        "IW1",
        "IW1/VV",
        "IW1/VV/gcp",
        "IW1/VV/attitude",
        "IW1/VV/orbit",
        "IW1/VV/calibration",
    }

    res = sentinel1.open_dataset(zip_urlpath)

    assert isinstance(res, xr.Dataset)
    assert set(res.attrs["subgroups"]) >= expected_groups

    res = sentinel1.open_dataset(zip_urlpath, group="IW1/VV/orbit")

    assert isinstance(res, xr.Dataset)
    assert res.dims == {"axis": 3, "azimuth_time": 17}

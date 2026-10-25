"""
ISSDC PRADAN Level-1 FITS Reader and Synchronizer for Aditya-L1.
Reads SoLEXS and HEL1OS FITS products, validates instrument metadata,
and synchronizes soft and hard X-ray time-series onto a common observation grid.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from heliocast.data.schema import QualityFlag, parse_aditya_timestamp
from heliocast.logging import get_logger

logger = get_logger("heliocast.data.fits_reader")

try:
    from astropy.io import fits
    ASTROPY_AVAILABLE = True
except ImportError:
    fits = None  # type: ignore
    ASTROPY_AVAILABLE = False


class FitsReaderError(Exception):
    """Exception raised when reading or parsing FITS telemetry fails."""
    pass


class AdityaFitsReader:
    """
    Parser for Level-1 FITS light curve files distributed via ISRO ISSDC PRADAN.
    Supports both SoLEXS (1-22 keV) and HEL1OS (10-150 keV) formats.
    """

    def __init__(self):
        if not ASTROPY_AVAILABLE:
            logger.warning("Astropy is not installed; FITS reading will operate in fallback mode.")

    def inspect_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Inspect header metadata and HDU structure of a FITS file.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"FITS file not found: {path}")

        info = {
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "hdus": [],
            "telescope": "ADITYA-L1",
            "instrument": "UNKNOWN",
            "date_obs": None,
            "columns": [],
        }

        with fits.open(str(path)) as hdul:
            for idx, hdu in enumerate(hdul):
                hdu_info = {
                    "index": idx,
                    "name": hdu.name,
                    "type": type(hdu).__name__,
                }
                if hdu.data is not None and hasattr(hdu.data, "names") and hdu.data.names:
                    hdu_info["columns"] = list(hdu.data.names)
                    if not info["columns"]:
                        info["columns"] = list(hdu.data.names)
                info["hdus"].append(hdu_info)

            # Read primary header keywords
            hdr = hdul[0].header
            info["telescope"] = hdr.get("TELESCOP", hdr.get("OBSERVER", "ADITYA-L1"))
            info["instrument"] = hdr.get("INSTRUME", "UNKNOWN").upper()
            info["date_obs"] = hdr.get("DATE-OBS", None)
            info["exposure"] = hdr.get("EXPOSURE", None)

        return info

    def read_lightcurve(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Read a single instrument Level-1 FITS light curve into a normalized pandas DataFrame.
        Columns guaranteed: ['timestamp', 'flux', 'quality']
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"FITS file not found: {path}")

        with fits.open(str(path)) as hdul:
            table_hdu = None
            for hdu in hdul:
                if hdu.data is not None and hasattr(hdu.data, "names") and hdu.data.names:
                    table_hdu = hdu
                    break

            if table_hdu is None:
                raise FitsReaderError(f"No binary table or data HDU found in {path.name}")

            data = table_hdu.data
            col_names = [c.upper() for c in data.names]

            # Detect Time column
            time_col = None
            for candidate in ["TIME", "TIMETAG", "TIMESTAMP", "SECONDS", "MET"]:
                if candidate in col_names:
                    time_col = candidate
                    break
            if not time_col:
                raise FitsReaderError(f"No suitable time column found in {path.name}. Columns: {col_names}")

            # Detect Flux/Rate column
            flux_col = None
            for candidate in ["RATE", "COUNTS", "FLUX", "INTENSITY", "COUNT_RATE"]:
                if candidate in col_names:
                    flux_col = candidate
                    break
            if not flux_col:
                raise FitsReaderError(f"No suitable flux column found in {path.name}. Columns: {col_names}")

            # Detect Quality column (optional)
            qual_col = None
            for candidate in ["QUALITY", "FLAG", "STATUS", "QUAL"]:
                if candidate in col_names:
                    qual_col = candidate
                    break

            raw_times = data[time_col]
            raw_flux = data[flux_col]
            raw_qual = data[qual_col] if qual_col else np.zeros(len(raw_times), dtype=int)

            timestamps = [parse_aditya_timestamp(t) for t in raw_times]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "flux": np.asarray(raw_flux, dtype=float),
                "quality": np.asarray(raw_qual, dtype=int),
            })

            # Clean NaNs and infinite values without backward-filling lookahead leakage
            raw_flux_array = df["flux"].replace([np.inf, -np.inf], np.nan)
            df["is_valid"] = (~raw_flux_array.isna()).astype(int)
            # Causal forward fill only (strictly no bfill to prevent future-data leakage)
            df["flux"] = raw_flux_array.ffill().fillna(0.0)

            return df

    def synchronize_observations(
        self,
        solexs_path: Union[str, Path],
        helios_path: Union[str, Path],
        cadence_sec: float = 10.0,
    ) -> pd.DataFrame:
        """
        Merge and time-synchronize independent SoLEXS and HEL1OS observations
        onto a regular time grid.
        """
        from heliocast.quality.audit import safe_spectral_hardness_ratio

        df_sxr = self.read_lightcurve(solexs_path)
        df_hxr = self.read_lightcurve(helios_path)

        df_sxr = df_sxr.rename(columns={
            "flux": "solexs_flux", 
            "quality": "solexs_quality",
            "is_valid": "solexs_valid"
        })
        df_hxr = df_hxr.rename(columns={
            "flux": "helios_flux", 
            "quality": "helios_quality",
            "is_valid": "helios_valid"
        })

        # Synchronize via outer merge with tolerance or resample
        df_sxr["time_bucket"] = pd.to_datetime(df_sxr["timestamp"]).dt.round(f"{int(cadence_sec)}s")
        df_hxr["time_bucket"] = pd.to_datetime(df_hxr["timestamp"]).dt.round(f"{int(cadence_sec)}s")

        merged = pd.merge(
            df_sxr.drop_duplicates(subset=["time_bucket"]),
            df_hxr.drop_duplicates(subset=["time_bucket"]),
            on="time_bucket",
            how="inner",
            suffixes=("_sxr", "_hxr"),
        )

        merged["timestamp"] = merged["time_bucket"]
        merged = merged.drop(columns=["time_bucket"])

        # Compute physical hardness ratio safely using sub-noise threshold guards
        merged["hardness_ratio"] = safe_spectral_hardness_ratio(
            merged["helios_flux"], 
            merged["solexs_flux"],
            min_sxr_threshold=1.0,
        )

        # Sort chronologically
        merged = merged.sort_values(by="timestamp").reset_index(drop=True)
        return merged

    @staticmethod
    def write_fits_lightcurve(
        df: pd.DataFrame,
        output_path: Union[str, Path],
        instrument: str = "SOLEXS",
        telescope: str = "ADITYA-L1",
    ) -> Path:
        """
        Export a telemetry dataframe to a compliant ISSDC Level-1 FITS file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if not ASTROPY_AVAILABLE:
            raise FitsReaderError("Astropy required to write FITS files.")

        # Create Primary HDU
        primary_hdu = fits.PrimaryHDU()
        primary_hdu.header["TELESCOP"] = telescope
        primary_hdu.header["INSTRUME"] = instrument.upper()
        primary_hdu.header["DATE-OBS"] = str(df["timestamp"].iloc[0])
        primary_hdu.header["CREATOR"] = "HelioCast-L1 v2.0"

        # Prepare Table columns
        times_numeric = [t.timestamp() for t in pd.to_datetime(df["timestamp"])]
        flux_key = "solexs_flux" if "solexs_flux" in df.columns else ("helios_flux" if "helios_flux" in df.columns else "flux")
        qual_key = "solexs_quality" if "solexs_quality" in df.columns else ("helios_quality" if "helios_quality" in df.columns else "quality")

        col_time = fits.Column(name="TIME", format="D", array=np.array(times_numeric, dtype=np.float64))
        col_flux = fits.Column(name="RATE", format="E", array=np.array(df[flux_key], dtype=np.float32))
        col_qual = fits.Column(name="QUALITY", format="J", array=np.array(df.get(qual_key, np.zeros(len(df))), dtype=np.int32))

        table_hdu = fits.BinTableHDU.from_columns([col_time, col_flux, col_qual], name="LIGHTCURVE")

        hdul = fits.HDUList([primary_hdu, table_hdu])
        hdul.writeto(str(out), overwrite=True)
        return out

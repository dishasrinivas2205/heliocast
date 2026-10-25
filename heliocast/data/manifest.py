"""
Aditya-L1 Data Ingestion Manifest and File Provenance Tracker.
Calculates cryptographic checksums (SHA-256), validates FITS / CSV file formats,
extracts observation intervals, and tracks ingestion history without inventing data.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from heliocast.logging import get_logger

logger = get_logger("heliocast.data.manifest")


@dataclass
class ManifestRecord:
    """Provenance and validation record for an individual telemetry product."""
    file_name: str
    file_path: str
    sha256_checksum: str
    size_bytes: int
    instrument: str             # SOLEXS, HEL1OS, or UNKNOWN
    product_level: str          # LEVEL1, LEVEL2, CALIBRATED
    format_type: str            # FITS, CSV, ASCII
    observation_start: Optional[str]
    observation_end: Optional[str]
    frame_count: int
    cadence_sec: float
    is_valid: bool
    validation_status: str      # VALIDATED, CORRUPT_HEADER, INCOMPLETE_DATA, MISSING_TIMESTAMPS
    ingestion_timestamp: str


class IngestionManifest:
    """
    Manages cryptographic provenance manifests for all Aditya-L1 data files.
    """

    def __init__(self, manifest_path: Union[str, Path] = "data/manifest.json"):
        self.manifest_path = Path(manifest_path)
        self.records: Dict[str, ManifestRecord] = {}
        self.load()

    @staticmethod
    def compute_sha256(file_path: Union[str, Path]) -> str:
        """Compute SHA-256 hash of a file deterministically."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def inspect_and_register_file(self, file_path: Union[str, Path]) -> ManifestRecord:
        """
        Inspect FITS or CSV file, validate format, and register into manifest.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        checksum = self.compute_sha256(path)
        size = path.stat().st_size
        fmt = "FITS" if path.suffix.lower() in [".fits", ".fit", ".fts"] else "CSV"
        now_utc = datetime.now(timezone.utc).isoformat()

        instrument = "UNKNOWN"
        start_obs = None
        end_obs = None
        frame_count = 0
        cadence_sec = 10.0
        is_valid = True
        status = "VALIDATED"

        if fmt == "FITS":
            try:
                from astropy.io import fits
                with fits.open(str(path)) as hdul:
                    hdr = hdul[0].header
                    instrument = str(hdr.get("INSTRUME", "UNKNOWN")).upper()
                    start_obs = str(hdr.get("DATE-OBS", "")) or None

                    # Check for data HDU
                    data_hdu = None
                    for hdu in hdul:
                        if hdu.data is not None and hasattr(hdu.data, "names") and hdu.data.names:
                            data_hdu = hdu
                            break

                    if data_hdu is not None:
                        frame_count = len(data_hdu.data)
                        if frame_count > 1 and "TIME" in data_hdu.data.names:
                            times = data_hdu.data["TIME"]
                            dt0 = times[1] - times[0]
                            cadence_sec = float(dt0) if dt0 > 0 else 10.0
                    else:
                        is_valid = False
                        status = "INCOMPLETE_DATA"
            except Exception as e:
                logger.error(f"Failed to inspect FITS file {path.name}: {e}")
                is_valid = False
                status = f"CORRUPT_HEADER: {str(e)}"
        else:
            try:
                import pandas as pd
                df = pd.read_csv(str(path))
                frame_count = len(df)
                if "timestamp" in df.columns:
                    start_obs = str(df["timestamp"].iloc[0])
                    end_obs = str(df["timestamp"].iloc[-1])
                if "solexs_flux" in df.columns and "helios_flux" in df.columns:
                    instrument = "SOLEXS_HEL1OS_JOINT"
                elif "solexs_flux" in df.columns:
                    instrument = "SOLEXS"
                elif "helios_flux" in df.columns:
                    instrument = "HEL1OS"
            except Exception as e:
                is_valid = False
                status = f"CORRUPT_CSV: {str(e)}"

        record = ManifestRecord(
            file_name=path.name,
            file_path=str(path.resolve()),
            sha256_checksum=checksum,
            size_bytes=size,
            instrument=instrument,
            product_level="LEVEL1",
            format_type=fmt,
            observation_start=start_obs,
            observation_end=end_obs,
            frame_count=frame_count,
            cadence_sec=cadence_sec,
            is_valid=is_valid,
            validation_status=status,
            ingestion_timestamp=now_utc,
        )

        self.records[checksum] = record
        self.save()
        logger.info(f"Registered file {path.name} in manifest (SHA-256: {checksum[:12]}...)")
        return record

    def save(self) -> None:
        """Persist manifest records to JSON."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self.records.items()}
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        """Load existing manifest if present."""
        if not self.manifest_path.exists():
            return
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = {k: ManifestRecord(**v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Could not load manifest from {self.manifest_path}: {e}")

    def list_records(self) -> List[ManifestRecord]:
        """Return list of all registered records."""
        return list(self.records.values())

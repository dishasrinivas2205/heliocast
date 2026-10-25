"""
Algorithmic Nowcaster Package for Aditya-L1.
Provides independent SoLEXS and HEL1OS detectors and Master Catalogue Fusion.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from heliocast.nowcaster.catalog import FlareCatalogDatabase
from heliocast.nowcaster.helios_detector import HeliosBurstDetector, HeliosFlareEvent
from heliocast.nowcaster.master_fusion import MasterCatalogueFusion, MasterFlareEvent
from heliocast.nowcaster.solexs_detector import SolexsFlareDetector, SolexsFlareEvent


class SolarFlareNowcaster:
    """
    Unified entrypoint for Step 3 Nowcasting pipeline.
    Runs independent detectors, fuses into master catalogue, and updates SQLite DB.
    """

    def __init__(self, db_path: str = "data/catalog/aditya_flares.db"):
        self.db = FlareCatalogDatabase(db_path=db_path)
        self.solexs_detector = SolexsFlareDetector()
        self.helios_detector = HeliosBurstDetector()
        self.fusion = MasterCatalogueFusion()

    def process_telemetry(
        self, df: pd.DataFrame
    ) -> Tuple[List[SolexsFlareEvent], List[HeliosFlareEvent], List[MasterFlareEvent]]:
        """
        Execute full nowcasting sequence:
        1. Independent SoLEXS detection
        2. Independent HEL1OS detection
        3. Master Fusion with Neupert verification
        4. Database persistence
        """
        solexs_evts = self.solexs_detector.detect(df)
        helios_evts = self.helios_detector.detect(df)
        master_evts = self.fusion.fuse(solexs_evts, helios_evts, df)

        # Persist to database
        self.db.store_solexs_events(solexs_evts)
        self.db.store_helios_events(helios_evts)
        self.db.store_master_events(master_evts)

        return solexs_evts, helios_evts, master_evts

    def get_master_catalog(self) -> pd.DataFrame:
        """Retrieve stored master catalog."""
        return self.db.get_master_catalog_df()


__all__ = [
    "SolarFlareNowcaster",
    "SolexsFlareDetector",
    "SolexsFlareEvent",
    "HeliosBurstDetector",
    "HeliosFlareEvent",
    "MasterCatalogueFusion",
    "MasterFlareEvent",
    "FlareCatalogDatabase",
]

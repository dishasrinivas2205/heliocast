"""
Physics-Based Aditya-L1 Telemetry Simulator.
Synthesizes coupled SoLEXS (Soft X-ray, 1-22 keV) and HEL1OS (Hard X-ray, 10-150 keV)
light curves adhering strictly to the solar Neupert Effect:
d/dt F_SXR(t) ~ F_HXR(t) during the impulsive energy deposition phase.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from heliocast.data.fits_reader import AdityaFitsReader
from heliocast.data.schema import QualityFlag
from heliocast.logging import get_logger

logger = get_logger("heliocast.data.synthetic")


class SolarFlareSimulator:
    """
    Simulates high-fidelity Aditya-L1 dual X-ray telemetry.
    Capable of synthesizing A, B, C, M, and X-class solar flares with
    accurate Neupert physics, Poisson noise, and quality flag bitmasks.
    """

    # Physical scaling of peak flux (counts/sec on SoLEXS Silicon Drift Detector)
    CLASS_PEAKS = {
        "A": (15.0, 45.0),
        "B": (50.0, 250.0),
        "C": (350.0, 2400.0),
        "M": (3000.0, 22000.0),
        "X": (28000.0, 150000.0),
    }

    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)

    def generate_stream(
        self,
        duration_hours: float = 6.0,
        cadence_sec: float = 10.0,
        start_time: Optional[datetime] = None,
        flare_events: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Generate time-series stream with specified or randomly generated solar flares.
        """
        if start_time is None:
            # Default to historic solar maximum observation: May 14, 2024 (Aditya-L1 observed X-class storms)
            start_time = datetime(2024, 5, 14, 8, 0, 0, tzinfo=timezone.utc)

        total_steps = int((duration_hours * 3600) / cadence_sec)
        times = [start_time + timedelta(seconds=i * cadence_sec) for i in range(total_steps)]

        # Base quiet-Sun background (thermal corona baseline)
        # SoLEXS quiet baseline: ~120-180 counts/sec
        # HEL1OS quiet non-thermal baseline: ~15-30 counts/sec
        solexs_base = 150.0 + 10.0 * np.sin(np.linspace(0, 3 * np.pi, total_steps))
        helios_base = 22.0 + 3.0 * np.cos(np.linspace(0, 2 * np.pi, total_steps))

        # Add realistic colored background fluctuations
        solexs_flux = solexs_base + self.rng.normal(0, 3.5, total_steps)
        helios_flux = helios_base + self.rng.normal(0, 1.8, total_steps)

        solexs_quality = np.zeros(total_steps, dtype=int)
        helios_quality = np.zeros(total_steps, dtype=int)
        flare_active = np.zeros(total_steps, dtype=bool)
        flare_classes = [None] * total_steps

        # Default flare events if not explicitly supplied
        if flare_events is None:
            flare_events = []
            if duration_hours >= 1.0:
                # Event 1: Precursor + C4.8 flare at T + 1.25 hours
                flare_events.append({
                    "class": "C",
                    "magnitude": 4.8,
                    "peak_step": int((1.25 * 3600) / cadence_sec),
                    "rise_min": 14.0,
                    "decay_min": 28.0,
                    "neupert_coupling": 0.88,
                })
            if duration_hours >= 3.5:
                # Event 2: Major M2.5 eruptive flare at T + 3.8 hours
                flare_events.append({
                    "class": "M",
                    "magnitude": 2.5,
                    "peak_step": int((3.8 * 3600) / cadence_sec),
                    "rise_min": 18.0,
                    "decay_min": 45.0,
                    "neupert_coupling": 0.94,
                })
            if duration_hours >= 8.0:
                # Event 3: Extreme X1.2 solar flare
                flare_events.append({
                    "class": "X",
                    "magnitude": 1.2,
                    "peak_step": int((7.5 * 3600) / cadence_sec),
                    "rise_min": 22.0,
                    "decay_min": 65.0,
                    "neupert_coupling": 0.96,
                })

        ground_truth_records = []

        for fl in flare_events:
            fl_class = fl.get("class", "C")
            mag = fl.get("magnitude", 5.0)
            peak_step = fl["peak_step"]
            if peak_step >= total_steps:
                continue

            rise_steps = max(10, int((fl.get("rise_min", 15.0) * 60) / cadence_sec))
            decay_steps = max(20, int((fl.get("decay_min", 30.0) * 60) / cadence_sec))
            start_step = max(0, peak_step - rise_steps)
            end_step = min(total_steps, peak_step + decay_steps)

            # Determine peak counts based on flare class and magnitude
            c_low, c_high = self.CLASS_PEAKS[fl_class]
            peak_amp = c_low + (c_high - c_low) * (min(mag, 9.9) / 10.0)

            # Thermal Soft X-ray profile: smooth quadratic-cubic rise, exponential decay
            t_rise = np.linspace(0, 1, peak_step - start_step)
            # Pre-flare gradual thermal heating precursor signature:
            rise_profile = peak_amp * (3 * t_rise**2 - 2 * t_rise**3)

            t_decay = np.linspace(0, (end_step - peak_step) * cadence_sec, end_step - peak_step)
            decay_time_constant = (decay_steps * cadence_sec) / 2.8
            decay_profile = peak_amp * np.exp(-t_decay / decay_time_constant)

            sxr_flare_profile = np.concatenate([rise_profile, decay_profile])
            actual_len = min(len(sxr_flare_profile), total_steps - start_step)
            solexs_flux[start_step : start_step + actual_len] += sxr_flare_profile[:actual_len]

            # Physical Neupert Effect for Hard X-rays (HEL1OS):
            # F_HXR(t) ~ d/dt F_SXR(t) strictly during the impulsive phase
            d_sxr = np.gradient(sxr_flare_profile)
            d_sxr_positive = np.maximum(0.0, d_sxr)
            coupling = fl.get("neupert_coupling", 0.90)

            # HEL1OS impulsive burst peak scaling
            hxr_scale = (peak_amp * 0.12 * coupling) / max(1e-3, np.max(d_sxr_positive))
            hxr_impulse = d_sxr_positive * hxr_scale

            helios_flux[start_step : start_step + actual_len] += hxr_impulse[:actual_len]
            flare_active[start_step : start_step + actual_len] = True

            full_class_name = f"{fl_class}{mag:.1f}"
            for idx in range(start_step, min(total_steps, start_step + actual_len)):
                flare_classes[idx] = full_class_name

            ground_truth_records.append({
                "event_id": f"AL1-{times[peak_step].strftime('%Y%m%d-%H%M%S')}",
                "flare_class": full_class_name,
                "start_time": times[start_step],
                "peak_time": times[peak_step],
                "end_time": times[min(total_steps - 1, end_step)],
                "peak_step": peak_step,
                "solexs_peak_counts": float(solexs_flux[peak_step]),
                "helios_peak_counts": float(np.max(helios_flux[start_step : peak_step + 1])),
                "neupert_coupling": coupling,
            })

        # Inject realistic Poisson photon noise
        solexs_flux = np.maximum(5.0, solexs_flux)
        helios_flux = np.maximum(2.0, helios_flux)
        solexs_flux = self.rng.poisson(solexs_flux).astype(float)
        helios_flux = self.rng.poisson(helios_flux).astype(float)

        # Inject occasional cosmic-ray glitch (single-step spike to test Neupert discriminator)
        if total_steps > 150:
            glitch_idx = int(total_steps * 0.45)
            if not flare_active[glitch_idx]:
                solexs_flux[glitch_idx] += 800.0  # False SXR glitch without HXR counterpart
                solexs_quality[glitch_idx] |= QualityFlag.PARTICLE_SPIKE

        # Hardness Ratio: F_HXR / max(F_SXR, 1e-3)
        hardness_ratio = helios_flux / np.maximum(solexs_flux, 1e-3)

        df = pd.DataFrame({
            "timestamp": times,
            "solexs_flux": solexs_flux,
            "helios_flux": helios_flux,
            "hardness_ratio": hardness_ratio,
            "solexs_quality": solexs_quality,
            "helios_quality": helios_quality,
            "flare_active": flare_active,
            "flare_class": flare_classes,
        })

        return df, ground_truth_records

    def generate_and_save_sample_fits(
        self,
        output_dir: Union[str, Path] = "data/sample",
        duration_hours: float = 4.0,
    ) -> Tuple[Path, Path]:
        """
        Generate sample synthetic Level-1 FITS files for SoLEXS and HEL1OS.
        Useful for immediate offline validation, testing, and judge demonstrations.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        df, _ = self.generate_stream(duration_hours=duration_hours, cadence_sec=10.0)

        solexs_path = out_dir / "aditya_solexs_level1_sample.fits"
        helios_path = out_dir / "aditya_hel1os_level1_sample.fits"

        AdityaFitsReader.write_fits_lightcurve(df, solexs_path, instrument="SOLEXS")
        AdityaFitsReader.write_fits_lightcurve(df, helios_path, instrument="HEL1OS")

        logger.info(f"Generated sample FITS: {solexs_path.name} & {helios_path.name}")
        return solexs_path, helios_path

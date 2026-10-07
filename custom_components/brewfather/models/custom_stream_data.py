from typing import Optional


class custom_stream_data:
    """Brewfather Custom Stream payload.

    Field names follow Brewfather's published Custom Stream contract. Optional
    values remain None until a configured Home Assistant source can provide a
    valid value.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.temp: Optional[float] = None
        self.aux_temp: Optional[float] = None
        self.ext_temp: Optional[float] = None
        self.temp_unit: Optional[str] = None
        self.gravity: Optional[float] = None
        self.gravity_unit: Optional[str] = None
        self.temp_target: Optional[float] = None
        self.gravity_target: Optional[float] = None
        self.device_source: Optional[str] = None
        self.report_source: Optional[str] = None

from pydantic import BaseModel, Field

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class ThemeSettingsOut(BaseModel):
    light_primary_color: str
    light_secondary_color: str
    dark_primary_color: str
    dark_secondary_color: str


class ThemeSettingsUpdateRequest(BaseModel):
    light_primary_color: str = Field(pattern=HEX_COLOR_PATTERN)
    light_secondary_color: str = Field(pattern=HEX_COLOR_PATTERN)
    dark_primary_color: str = Field(pattern=HEX_COLOR_PATTERN)
    dark_secondary_color: str = Field(pattern=HEX_COLOR_PATTERN)

from pydantic import BaseModel

from app.models.instance import WhatsAppProvider


class WhatsAppConnectionOut(BaseModel):
    provider: WhatsAppProvider | None
    whatsapp_instance_name: str | None
    meta_phone_number_id: str | None


class EvolutionCreateRequest(BaseModel):
    instance_name: str


class EvolutionQrOut(BaseModel):
    base64: str | None
    code: str | None
    pairing_code: str | None
    state: str


class EvolutionStatusOut(BaseModel):
    state: str


class MetaConnectRequest(BaseModel):
    phone_number_id: str
    access_token: str


class MetaConnectOut(BaseModel):
    display_phone_number: str
    verified_name: str

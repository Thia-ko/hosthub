from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance, require_admin, require_cf_access_header
from app.db.session import get_db
from app.models.instance import Instance, WhatsAppProvider
from app.models.user import User
from app.schemas.whatsapp_connection import (
    EvolutionCreateRequest,
    EvolutionQrOut,
    EvolutionStatusOut,
    MetaConnectOut,
    MetaConnectRequest,
    WhatsAppConnectionOut,
)
from app.services.whatsapp_channel import (
    WhatsAppChannelError,
    create_evolution_instance,
    delete_evolution_instance,
    get_evolution_qr,
    get_evolution_status,
    validate_meta_credentials,
)

router = APIRouter(prefix="/instances/{instance_id}/whatsapp-connection", tags=["whatsapp-connection"])


def _connection_out(instance: Instance) -> WhatsAppConnectionOut:
    return WhatsAppConnectionOut(
        provider=instance.whatsapp_provider,
        whatsapp_instance_name=instance.whatsapp_instance_name,
        meta_phone_number_id=instance.meta_phone_number_id,
    )


@router.get("", response_model=WhatsAppConnectionOut)
async def get_whatsapp_connection(instance: Instance = Depends(get_owned_instance)) -> WhatsAppConnectionOut:
    return _connection_out(instance)


@router.post(
    "/evolution/instance",
    response_model=EvolutionQrOut,
    dependencies=[Depends(require_cf_access_header)],
)
async def create_evolution_connection(
    payload: EvolutionCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> EvolutionQrOut:
    try:
        created = await create_evolution_instance(payload.instance_name)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    instance.whatsapp_provider = WhatsAppProvider.EVOLUTION
    instance.whatsapp_instance_name = payload.instance_name
    await db.commit()

    # The create response usually carries the QR code inline (qrcode:true) - only fall back to a
    # separate fetch if that data isn't there for whatever reason (e.g. an already-existing
    # instance name on the Evolution side, which some versions still create-and-return-200 for).
    qrcode_section = created.get("qrcode") if isinstance(created.get("qrcode"), dict) else created
    base64_value = qrcode_section.get("base64") or created.get("base64")
    code_value = qrcode_section.get("code") or created.get("code")
    pairing_code = qrcode_section.get("pairingCode") or created.get("pairingCode")

    if not base64_value and not code_value:
        try:
            fetched = await get_evolution_qr(payload.instance_name)
            base64_value = fetched.get("base64")
            code_value = fetched.get("code")
            pairing_code = fetched.get("pairing_code")
        except WhatsAppChannelError:
            pass

    try:
        state = await get_evolution_status(payload.instance_name)
    except WhatsAppChannelError:
        state = "connecting"

    return EvolutionQrOut(base64=base64_value, code=code_value, pairing_code=pairing_code, state=state)


@router.get("/evolution/qr", response_model=EvolutionQrOut)
async def get_evolution_connection_qr(instance: Instance = Depends(get_owned_instance)) -> EvolutionQrOut:
    if not instance.whatsapp_instance_name:
        raise HTTPException(status_code=400, detail="Nenhuma instancia Evolution configurada.")
    try:
        qr = await get_evolution_qr(instance.whatsapp_instance_name)
        state = await get_evolution_status(instance.whatsapp_instance_name)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return EvolutionQrOut(base64=qr.get("base64"), code=qr.get("code"), pairing_code=qr.get("pairing_code"), state=state)


@router.get("/evolution/status", response_model=EvolutionStatusOut)
async def get_evolution_connection_status(instance: Instance = Depends(get_owned_instance)) -> EvolutionStatusOut:
    if not instance.whatsapp_instance_name:
        raise HTTPException(status_code=400, detail="Nenhuma instancia Evolution configurada.")
    try:
        state = await get_evolution_status(instance.whatsapp_instance_name)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return EvolutionStatusOut(state=state)


@router.delete(
    "/evolution/instance",
    response_model=WhatsAppConnectionOut,
    dependencies=[Depends(require_cf_access_header)],
)
async def delete_evolution_connection(
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> WhatsAppConnectionOut:
    if not instance.whatsapp_instance_name:
        raise HTTPException(status_code=400, detail="Nenhuma instancia Evolution configurada.")
    try:
        await delete_evolution_instance(instance.whatsapp_instance_name)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    instance.whatsapp_instance_name = None
    instance.whatsapp_provider = None
    await db.commit()
    return _connection_out(instance)


@router.post(
    "/meta/test",
    response_model=MetaConnectOut,
    dependencies=[Depends(require_cf_access_header)],
)
async def test_meta_connection(
    payload: MetaConnectRequest,
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MetaConnectOut:
    try:
        result = await validate_meta_credentials(payload.phone_number_id, payload.access_token)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    display_phone_number = result.get("display_phone_number")
    verified_name = result.get("verified_name")
    if not display_phone_number or not verified_name:
        raise HTTPException(
            status_code=400,
            detail="Falha ao validar credenciais da API Oficial (Meta): resposta incompleta.",
        )

    instance.whatsapp_provider = WhatsAppProvider.META_CLOUD
    instance.meta_phone_number_id = payload.phone_number_id
    instance.meta_access_token = payload.access_token
    await db.commit()

    return MetaConnectOut(display_phone_number=display_phone_number, verified_name=verified_name)


@router.delete(
    "/meta/instance",
    response_model=WhatsAppConnectionOut,
    dependencies=[Depends(require_cf_access_header)],
)
async def delete_meta_connection(
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> WhatsAppConnectionOut:
    instance.whatsapp_provider = None
    instance.meta_phone_number_id = None
    instance.meta_access_token = None
    await db.commit()
    return _connection_out(instance)

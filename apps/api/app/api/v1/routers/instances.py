import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_owned_instance, require_admin, require_cf_access_header
from app.core.security import hash_password
from app.core.slug import slugify
from app.db.session import get_db
from app.models.instance import Instance, InstanceStatus
from app.models.instance_member import InstanceMember, InstanceMemberRole
from app.models.user import User, UserRole
from app.schemas.instance import (
    ClientPasswordResetOut,
    InstanceCreateRequest,
    InstanceCreateResponse,
    InstanceDetailOut,
    InstanceOut,
    InstanceUpdateRequest,
)
from app.services.plans import get_features

router = APIRouter(prefix="/instances", tags=["instances"])


async def _unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while (await db.execute(select(Instance).where(Instance.slug == slug))).scalar_one_or_none() is not None:
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


async def _detail_out(db: AsyncSession, instance: Instance, owner_email: str | None = None) -> InstanceDetailOut:
    if owner_email is None:
        owner = await db.get(User, instance.owner_user_id)
        owner_email = owner.email if owner else ""
    features = get_features(instance)
    return InstanceDetailOut(
        id=instance.id,
        name=instance.name,
        slug=instance.slug,
        status=instance.status,
        owner_user_id=instance.owner_user_id,
        owner_email=owner_email,
        created_at=instance.created_at,
        ai_assist_daily_token_limit=instance.ai_assist_daily_token_limit,
        webhook_token=instance.webhook_token,
        whatsapp_instance_name=instance.whatsapp_instance_name,
        auto_generate_prompt=instance.auto_generate_prompt,
        auto_gen_conversation_threshold=instance.auto_gen_conversation_threshold,
        auto_gen_interval=instance.auto_gen_interval,
        last_auto_gen_at=instance.last_auto_gen_at,
        whatsapp_provider=instance.whatsapp_provider,
        meta_phone_number_id=instance.meta_phone_number_id,
        plan=instance.plan,
        ai_enabled_override=instance.ai_enabled_override,
        campaigns_enabled_override=instance.campaigns_enabled_override,
        api_access_enabled_override=instance.api_access_enabled_override,
        ai_enabled=features.ai_enabled,
        campaigns_enabled=features.campaigns_enabled,
        api_access_enabled=features.api_access_enabled,
    )


@router.get("", response_model=list[InstanceOut])
async def list_instances(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[InstanceOut]:
    query = select(Instance, User.email).join(User, User.id == Instance.owner_user_id)
    if user.role != UserRole.ADMIN:
        query = query.join(InstanceMember, InstanceMember.instance_id == Instance.id).where(
            InstanceMember.user_id == user.id
        )
    result = await db.execute(query.order_by(Instance.created_at.desc()))
    return [
        InstanceOut(
            id=instance.id,
            name=instance.name,
            slug=instance.slug,
            status=instance.status,
            owner_user_id=instance.owner_user_id,
            owner_email=owner_email,
            created_at=instance.created_at,
        )
        for instance, owner_email in result.all()
    ]


@router.post("", response_model=InstanceCreateResponse, dependencies=[Depends(require_cf_access_header)])
async def create_instance(
    payload: InstanceCreateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> InstanceCreateResponse:
    result = await db.execute(select(User).where(User.email == payload.client_email))
    client = result.scalar_one_or_none()
    generated_password: str | None = None

    if client is None:
        generated_password = payload.client_password or secrets.token_urlsafe(9)
        client = User(
            email=payload.client_email,
            password_hash=hash_password(generated_password),
            role=UserRole.CLIENT,
            full_name=payload.client_full_name,
        )
        db.add(client)
        await db.flush()
    elif client.role != UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este e-mail pertence a um administrador")

    instance = Instance(
        name=payload.name,
        slug=await _unique_slug(db, payload.name),
        owner_user_id=client.id,
        created_by_admin_id=admin.id,
    )
    db.add(instance)
    await db.flush()
    db.add(InstanceMember(instance_id=instance.id, user_id=client.id, role=InstanceMemberRole.OWNER))
    await db.commit()
    await db.refresh(instance)

    return InstanceCreateResponse(
        instance=await _detail_out(db, instance, owner_email=client.email),
        client_email=client.email,
        generated_password=generated_password,
    )


@router.get("/{instance_id}", response_model=InstanceDetailOut)
async def get_instance(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> InstanceDetailOut:
    return await _detail_out(db, instance)


@router.patch("/{instance_id}", response_model=InstanceDetailOut, dependencies=[Depends(require_cf_access_header)])
async def update_instance(
    payload: InstanceUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> InstanceDetailOut:
    if payload.name is not None:
        instance.name = payload.name
    if payload.status is not None:
        instance.status = payload.status
    if payload.ai_assist_daily_token_limit is not None:
        instance.ai_assist_daily_token_limit = payload.ai_assist_daily_token_limit
    if payload.whatsapp_instance_name is not None:
        instance.whatsapp_instance_name = payload.whatsapp_instance_name or None
    if payload.auto_generate_prompt is not None:
        instance.auto_generate_prompt = payload.auto_generate_prompt
    if payload.auto_gen_conversation_threshold is not None:
        instance.auto_gen_conversation_threshold = payload.auto_gen_conversation_threshold
    if payload.auto_gen_interval is not None:
        instance.auto_gen_interval = payload.auto_gen_interval
    if payload.plan is not None:
        instance.plan = payload.plan
    if payload.clear_ai_enabled_override:
        instance.ai_enabled_override = None
    elif payload.ai_enabled_override is not None:
        instance.ai_enabled_override = payload.ai_enabled_override
    if payload.clear_campaigns_enabled_override:
        instance.campaigns_enabled_override = None
    elif payload.campaigns_enabled_override is not None:
        instance.campaigns_enabled_override = payload.campaigns_enabled_override
    if payload.clear_api_access_enabled_override:
        instance.api_access_enabled_override = None
    elif payload.api_access_enabled_override is not None:
        instance.api_access_enabled_override = payload.api_access_enabled_override
    await db.commit()
    await db.refresh(instance)
    return await _detail_out(db, instance)


@router.delete("/{instance_id}", response_model=InstanceDetailOut, dependencies=[Depends(require_cf_access_header)])
async def archive_instance(
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> InstanceDetailOut:
    instance.status = InstanceStatus.ARCHIVED
    await db.commit()
    await db.refresh(instance)
    return await _detail_out(db, instance)


@router.post(
    "/{instance_id}/regenerate-webhook-token",
    response_model=InstanceDetailOut,
    dependencies=[Depends(require_cf_access_header)],
)
async def regenerate_webhook_token(
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> InstanceDetailOut:
    instance.webhook_token = secrets.token_urlsafe(32)
    await db.commit()
    await db.refresh(instance)
    return await _detail_out(db, instance)


@router.post(
    "/{instance_id}/reset-client-password",
    response_model=ClientPasswordResetOut,
    dependencies=[Depends(require_cf_access_header)],
)
async def reset_client_password(
    instance: Instance = Depends(get_owned_instance),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ClientPasswordResetOut:
    owner = await db.get(User, instance.owner_user_id)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")
    generated_password = secrets.token_urlsafe(9)
    owner.password_hash = hash_password(generated_password)
    await db.commit()
    return ClientPasswordResetOut(client_email=owner.email, generated_password=generated_password)

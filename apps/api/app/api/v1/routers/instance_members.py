import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_owned_instance, require_cf_access_header
from app.core.security import hash_password
from app.db.session import get_db
from app.models.instance import Instance
from app.models.instance_member import InstanceMember, InstanceMemberRole
from app.models.user import User, UserRole
from app.schemas.instance_member import (
    InstanceMemberInviteRequest,
    InstanceMemberInviteResponse,
    InstanceMemberOut,
    InstanceMembersOut,
)

router = APIRouter(prefix="/instances/{instance_id}/members", tags=["instance-members"])


async def _can_manage(db: AsyncSession, instance_id: uuid.UUID, user: User) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    result = await db.execute(
        select(InstanceMember).where(
            InstanceMember.instance_id == instance_id,
            InstanceMember.user_id == user.id,
            InstanceMember.role == InstanceMemberRole.OWNER,
        )
    )
    return result.scalar_one_or_none() is not None


def _require_manage(can_manage: bool) -> None:
    if not can_manage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o administrador ou o dono da instancia podem gerenciar a equipe",
        )


@router.get("", response_model=InstanceMembersOut)
async def list_members(
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstanceMembersOut:
    result = await db.execute(
        select(InstanceMember, User)
        .join(User, User.id == InstanceMember.user_id)
        .where(InstanceMember.instance_id == instance.id)
        .order_by(InstanceMember.created_at)
    )
    members = [
        InstanceMemberOut(
            id=member.id,
            user_id=member.user_id,
            email=member_user.email,
            full_name=member_user.full_name,
            role=member.role,
            created_at=member.created_at,
        )
        for member, member_user in result.all()
    ]
    return InstanceMembersOut(members=members, can_manage=await _can_manage(db, instance.id, user))


@router.post("", response_model=InstanceMemberInviteResponse, dependencies=[Depends(require_cf_access_header)])
async def invite_member(
    payload: InstanceMemberInviteRequest,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstanceMemberInviteResponse:
    _require_manage(await _can_manage(db, instance.id, user))

    result = await db.execute(select(User).where(User.email == payload.email))
    invitee = result.scalar_one_or_none()
    generated_password: str | None = None

    if invitee is None:
        generated_password = payload.password or secrets.token_urlsafe(9)
        invitee = User(
            email=payload.email,
            password_hash=hash_password(generated_password),
            role=UserRole.CLIENT,
            full_name=payload.full_name,
        )
        db.add(invitee)
        await db.flush()
    elif invitee.role != UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este e-mail pertence a um administrador")

    existing = await db.execute(
        select(InstanceMember).where(
            InstanceMember.instance_id == instance.id, InstanceMember.user_id == invitee.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este usuario ja faz parte da equipe")

    member = InstanceMember(instance_id=instance.id, user_id=invitee.id, role=InstanceMemberRole.MEMBER)
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return InstanceMemberInviteResponse(
        member=InstanceMemberOut(
            id=member.id,
            user_id=invitee.id,
            email=invitee.email,
            full_name=invitee.full_name,
            role=member.role,
            created_at=member.created_at,
        ),
        generated_password=generated_password,
    )


@router.delete("/{user_id}", response_model=dict, dependencies=[Depends(require_cf_access_header)])
async def remove_member(
    user_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _require_manage(await _can_manage(db, instance.id, user))

    result = await db.execute(
        select(InstanceMember).where(
            InstanceMember.instance_id == instance.id, InstanceMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")

    if member.role == InstanceMemberRole.OWNER:
        owner_count = await db.scalar(
            select(func.count()).select_from(InstanceMember).where(
                InstanceMember.instance_id == instance.id, InstanceMember.role == InstanceMemberRole.OWNER
            )
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="A instancia precisa de pelo menos um dono"
            )

    await db.delete(member)
    await db.commit()
    return {"removed": True}

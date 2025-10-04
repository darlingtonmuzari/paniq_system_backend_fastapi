#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from app.models.emergency import PanicRequest
from app.models.user import UserGroup, RegisteredUser
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check_requests():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PanicRequest)
            .options(
                selectinload(PanicRequest.group).selectinload(UserGroup.user)
            )
            .limit(5)
        )
        requests = result.scalars().all()
        print(f'Found {len(requests)} panic requests')
        
        for req in requests:
            print(f'Request ID: {req.id}')
            print(f'Group ID: {req.group_id}')
            print(f'Status: {req.status}')
            print(f'Service Type: {req.service_type}')
            if req.group and req.group.user:
                user = req.group.user
                print(f'Requester: {user.first_name} {user.last_name}')
            else:
                print('No user data found')
            print('---')

asyncio.run(check_requests())
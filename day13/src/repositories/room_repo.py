# src/repositories/room_repo.py
from typing import List, Optional
from ..domain.models import Room
from .base import BaseRepository


class RoomRepository(BaseRepository[Room]):
    def __init__(self):
        self._storage: dict[int, Room] = {}
        self._next_id = 1

    def get_by_id(self, id: int) -> Optional[Room]:
        return self._storage.get(id)

    def get_all(self, **filters) -> List[Room]:
        result = list(self._storage.values())
        
        if 'hotel_id' in filters:
            result = [r for r in result if r.hotel_id == filters['hotel_id']]
        if 'is_active' in filters:
            result = [r for r in result if r.is_active == filters['is_active']]
        
        return result

    def add(self, room: Room) -> Room:
        room.id = self._next_id  # Исправлено: room.id, а не Room.id
        self._storage[room.id] = room
        self._next_id += 1
        return room

    def update(self, room: Room) -> Room:
        if room.id not in self._storage:
            raise ValueError(f"Room with id {room.id} not found")
        self._storage[room.id] = room
        return room

    def delete(self, id: int) -> bool:
        if id in self._storage:
            del self._storage[id]
            return True
        return False

    def get_by_hotel(self, hotel_id: int, active_only: bool = True) -> List[Room]:
        """Получить все номера отеля"""
        result = [r for r in self._storage.values() if r.hotel_id == hotel_id]
        if active_only:
            result = [r for r in result if r.is_active]
        return result
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtGui import QIcon
import os

def toggle_favorite(character):
    character["favorite"] = not character.get("favorite", False)

def is_favorite(character):
    return character.get("favorite", False)

def render_character_item(character):
    name = character.get("name", "(이름 없음)")
    if character.get("favorite"):
        return f"★ {name}"
    return name

def sort_characters_with_favorite_priority(characters, key=lambda c: c.get("name", ""), reverse=False):
    favorites = sorted([c for c in characters if c.get("favorite")], key=key, reverse=reverse)
    normals = sorted([c for c in characters if not c.get("favorite")], key=key, reverse=reverse)
    return favorites + normals

def sort_characters(characters, mode="기본 정렬"):
    if not characters:  # 빈 리스트 처리
        return []

    def by_name(c): 
        return c.get("name", "").lower()

    # 즐겨찾기와 일반 항목 분리
    favorites = [c for c in characters if c.get("favorite", False)]
    normals = [c for c in characters if not c.get("favorite", False)]

    if mode == "오름차순 정렬":
        favorites.sort(key=by_name)
        normals.sort(key=by_name)
    elif mode == "내림차순 정렬":
        favorites.sort(key=by_name, reverse=True)
        normals.sort(key=by_name, reverse=True)
    elif mode == "커스텀 정렬":
        # 커스텀 정렬에서는 각 그룹 내 순서 유지
        pass
    else:  # 기본 정렬
        favorites.sort(key=by_name)
        normals.sort(key=by_name)

    # 항상 즐겨찾기가 먼저 오도록 합니다
    return favorites + normals

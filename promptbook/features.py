def sort_characters(characters, mode):
    """캐릭터 리스트를 지정된 모드로 정렬합니다."""
    if mode == "이름순":
        return sorted(characters, key=lambda x: x.get("name", ""))
    elif mode == "최근 수정순":
        return sorted(characters, key=lambda x: x.get("modified", ""), reverse=True)
    elif mode == "즐겨찾기":
        return sorted(characters, key=lambda x: (not x.get("favorite", False), x.get("name", "")))
    else:
        return characters 
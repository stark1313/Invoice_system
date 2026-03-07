# -*- coding: utf-8 -*-
"""숫자를 한글 금액으로 변환 (예: 1541280 -> 일백오십사만일천이백팔십원정)"""

_CR = ("", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")
_UNIT1 = ("", "십", "백", "천")
_UNIT2 = ("", "만", "억", "조")


def num_to_korean(n):
    """정수를 한글 숫자 문자열로 변환 (예: 1541280 -> 일백오십사만일천이백팔십, 120000 -> 일십이만)"""
    if n == 0:
        return "영"
    s = str(n)
    result = []
    len_s = len(s)
    for i, c in enumerate(s):
        d = int(c)
        pos = len_s - i - 1
        unit2_idx = pos // 4
        unit1_idx = pos % 4
        if d == 0:
            # 0 at ones place of a block: add block unit if current block has any non-zero
            if unit1_idx == 0 and unit2_idx > 0:
                block = s[max(0, i - 3) : i + 1]
                if block and int(block) > 0:
                    result.append(_UNIT2[unit2_idx])
            continue
        result.append(_CR[d])
        result.append(_UNIT1[unit1_idx])
        if unit1_idx == 0 and unit2_idx > 0:
            result.append(_UNIT2[unit2_idx])
    return "".join(result)


def amount_to_korean_won(n):
    """금액을 한글 원 단위로 변환 (예: 1541280 -> 金 일백오십사만일천이백팔십원 정)"""
    return "金 " + num_to_korean(n) + "원 정"

"""DUPR 場的分組與賽程（純函式，不碰資料庫）。

三種賽制：
  rotating  輪換搭檔雙打：每組 4～7 人一面場，4 人打 3 局、5 人打 5 局（每局 1 人輪空），
            每人和同組每個人盡量都搭檔一次；6、7 人每人打 4 局。
  fixed     固定搭檔雙打：兩人一隊，同組隊伍互打一輪（每組 2～5 隊）。
  singles   單打循環賽：同組每人互打一場（每組 2～7 人）。

分組一律依 DUPR 分數由高到低切成連續區段，分數相近的在同一組。
entry（參賽單位）：輪換搭檔、單打是 [球員]，固定搭檔是 [球員, 隊友]。
"""
import itertools
import math

FORMATS = {"rotating": "輪換搭檔", "fixed": "固定搭檔", "singles": "單打"}
GROUP_NAMES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# 5 人輪換搭檔：每局 1 人輪空，10 組搭檔各出現一次
FIVE = [(4, (0, 1), (2, 3)), (3, (0, 2), (1, 4)), (2, (0, 4), (1, 3)), (1, (0, 3), (2, 4)), (0, (1, 2), (3, 4))]


def entry_size(fmt: str) -> int:
    return 2 if fmt == "fixed" else 1


def min_group(fmt: str) -> int:
    return 4 if fmt == "rotating" else 2


def _split(items: list, groups: int) -> list[list]:
    """依序切成 groups 段，前面的段落多分到餘數。"""
    base, extra = divmod(len(items), groups)
    out, i = [], 0
    for g in range(groups):
        n = base + (1 if g < extra else 0)
        out.append(items[i:i + n])
        i += n
    return out


def plan_groups(fmt: str, entries: list[list[int]], rating: dict) -> list[list[list[int]]]:
    """entries 已依分數排序（高到低）；回傳各組的 entries。"""
    n = len(entries)
    if fmt == "rotating":
        if n < 4:
            raise ValueError("輪換搭檔至少需要 4 人")
        groups = n // 4  # 每組 4～7 人
    elif fmt == "fixed":
        if n < 2:
            raise ValueError("固定搭檔至少需要 2 隊（4 人）")
        groups = max(1, math.ceil(n / 5))  # 每組 2～5 隊，避免一組太多場
        while groups > 1 and n // groups < 2:
            groups -= 1
    else:
        if n < 2:
            raise ValueError("單打至少需要 2 人")
        groups = max(1, n // 4) if n >= 4 else 1
    return _split(entries, groups)


def pair_teams(players: list[int], rating: dict, partner_of: dict) -> list[list[int]]:
    """固定搭檔：先採用學生指定的隊友（雙方都已報名且沒被別人先配走），其餘依分數首尾配對讓各隊實力平均。"""
    teams, used = [], set()
    for p in players:
        q = partner_of.get(p)
        if p in used or not q or q in used or q not in players or q == p:
            continue
        teams.append([p, q])
        used.update((p, q))
    rest = [p for p in players if p not in used]
    if len(rest) % 2:
        raise ValueError("固定搭檔需要偶數人數，目前多出 1 人，請調整名單")
    while rest:
        teams.append([rest.pop(0), rest.pop(-1)])
    teams.sort(key=lambda t: -sum(rating.get(p) or 0 for p in t) / 2)
    return teams


def rotating_schedule(players: list[int]) -> list[dict]:
    k = len(players)
    if k == 4:
        a, b, c, d = players
        return [{"a": [a, b], "b": [c, d], "bye": []}, {"a": [a, c], "b": [b, d], "bye": []},
                {"a": [a, d], "b": [b, c], "bye": []}]
    if k == 5:
        return [{"a": [players[x] for x in ta], "b": [players[x] for x in tb], "bye": [players[bye]]}
                for bye, ta, tb in FIVE]
    # 6、7 人：共 k 局、每人剛好打 4 局、搭檔不重複，並讓同一人不連續輪空兩局（搜尋，最多幾千步）
    idx = list(range(k))
    options = []
    for four in itertools.combinations(idx, 4):
        a, b, c, d = four
        options += [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]
    played, used, chosen = [0] * k, set(), []

    def dfs() -> bool:
        if len(chosen) == k:
            return True
        last = set(idx) - set(chosen[-1][0] + chosen[-1][1]) if chosen else set()
        for ta, tb in options:
            four = ta + tb
            if any(played[p] >= 4 for p in four) or frozenset(ta) in used or frozenset(tb) in used:
                continue
            if last & (set(idx) - set(four)):
                continue  # 上一局輪空的人這局要上場
            for p in four:
                played[p] += 1
            used.update((frozenset(ta), frozenset(tb)))
            chosen.append((ta, tb))
            if dfs():
                return True
            chosen.pop()
            used.difference_update((frozenset(ta), frozenset(tb)))
            for p in four:
                played[p] -= 1
        return False

    if not dfs():
        raise ValueError(f"{k} 人無法排出輪換搭檔賽程")
    return [{"a": [players[x] for x in ta], "b": [players[x] for x in tb],
             "bye": [players[x] for x in idx if x not in ta + tb]} for ta, tb in chosen]


def round_robin(units: list) -> list[tuple]:
    """圓桌法：每個單位和其他單位各打一次，依輪次排序（同一輪沒人連打兩場）。"""
    items = list(units) + ([None] if len(units) % 2 else [])
    n = len(items)
    out = []
    for _ in range(n - 1):
        for i in range(n // 2):
            x, y = items[i], items[n - 1 - i]
            if x is not None and y is not None:
                out.append((x, y))
        items = [items[0], items[-1]] + items[1:-1]
    return out


def schedule(fmt: str, entries: list[list[int]]) -> list[dict]:
    """回傳一組的所有對戰：{"a": [球員], "b": [球員], "bye": [球員]}。"""
    if fmt == "rotating":
        return rotating_schedule([e[0] for e in entries])
    all_players = [p for e in entries for p in e]
    return [{"a": list(x), "b": list(y), "bye": [p for p in all_players if p not in x and p not in y]}
            for x, y in round_robin(entries)]


def score_problem(a, b, games_to: int, strict: bool) -> str | None:
    """比分檢查；strict（學員回報）時需符合「打到 N 分、領先 2 分」。"""
    try:
        a, b = int(a), int(b)
    except (TypeError, ValueError):
        return "請填寫雙方分數"
    if not (0 <= a <= 99 and 0 <= b <= 99):
        return "分數需介於 0～99"
    if a == b:
        return "比分不能平手"
    if strict:
        hi, lo = max(a, b), min(a, b)
        if hi < games_to:
            return f"這場打到 {games_to} 分，勝方需達 {games_to} 分"
        if hi - lo < 2 or (hi > games_to and hi - lo != 2):
            return f"需領先 2 分才算勝（例如 {games_to}:{games_to - 2} 或 {games_to + 1}:{games_to - 1}）"
    return None


def standings(fmt: str, entries: list[list[int]], games: list[dict]) -> list[dict]:
    """只計已確認的比分；依勝場、得失分差、得分排序。"""
    key = (lambda team: tuple(sorted(team))) if fmt == "fixed" else (lambda team: None)
    table = {}
    for e in entries:
        table[tuple(sorted(e))] = {"players": list(e), "played": 0, "won": 0, "lost": 0, "pf": 0, "pa": 0}
    for g in games:
        if g["status"] != "confirmed":
            continue
        for side, other, pf, pa in (("a", "b", g["score_a"], g["score_b"]), ("b", "a", g["score_b"], g["score_a"])):
            units = [key(g[side])] if fmt == "fixed" else [(p,) for p in g[side] if p]
            for u in units:
                row = table.get(u)
                if not row:
                    continue
                row["played"] += 1
                row["won"] += pf > pa
                row["lost"] += pf < pa
                row["pf"] += pf
                row["pa"] += pa
    rows = list(table.values())
    for r in rows:
        r["diff"] = r["pf"] - r["pa"]
    rows.sort(key=lambda r: (-r["won"], -r["diff"], -r["pf"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows

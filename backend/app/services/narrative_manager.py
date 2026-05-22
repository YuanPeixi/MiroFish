"""
叙事快照与分支管理
用于影视结局协同推理的最小可运行闭环
"""

import json
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config


def _now() -> str:
    return datetime.now().isoformat()


class NarrativeManager:
    """叙事状态管理器（文件持久化）"""

    PROJECT_ID_PATTERN = re.compile(r"^proj_[A-Za-z0-9_-]{3,80}$")

    @classmethod
    def _project_dir(cls, project_id: str) -> str:
        cls._validate_project_id(project_id)
        projects_root = os.path.abspath(os.path.join(Config.UPLOAD_FOLDER, "projects"))
        project_dir = os.path.abspath(os.path.join(projects_root, project_id))
        if not project_dir.startswith(projects_root + os.sep):
            raise ValueError("非法 project_id")
        return project_dir

    @classmethod
    def _validate_project_id(cls, project_id: str) -> None:
        if not isinstance(project_id, str) or not cls.PROJECT_ID_PATTERN.match(project_id):
            raise ValueError("非法 project_id")

    @classmethod
    def _narrative_dir(cls, project_id: str) -> str:
        return os.path.join(cls._project_dir(project_id), "narrative")

    @classmethod
    def _state_path(cls, project_id: str) -> str:
        return os.path.join(cls._narrative_dir(project_id), "state.json")

    @classmethod
    def _ensure_project_exists(cls, project_id: str) -> None:
        if not os.path.isdir(cls._project_dir(project_id)):
            raise ValueError(f"项目不存在: {project_id}")

    @classmethod
    def _ensure_narrative_dir(cls, project_id: str) -> None:
        cls._ensure_project_exists(project_id)
        os.makedirs(cls._narrative_dir(project_id), exist_ok=True)

    @classmethod
    def _default_state(cls, project_id: str) -> Dict[str, Any]:
        return {
            "project_id": project_id,
            "created_at": _now(),
            "updated_at": _now(),
            "current_snapshot_id": None,
            "selected_branch_id": None,
            "branches": [],
            "snapshots": [],
            "meta": {
                "version": 1
            }
        }

    @classmethod
    def load(cls, project_id: str) -> Dict[str, Any]:
        cls._ensure_narrative_dir(project_id)
        state_path = cls._state_path(project_id)
        if not os.path.exists(state_path):
            state = cls._default_state(project_id)
            cls.save(project_id, state)
            return state

        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def save(cls, project_id: str, state: Dict[str, Any]) -> None:
        cls._ensure_narrative_dir(project_id)
        state["updated_at"] = _now()
        with open(cls._state_path(project_id), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @classmethod
    def _find_snapshot(cls, state: Dict[str, Any], snapshot_id: str) -> Optional[Dict[str, Any]]:
        return next((s for s in state["snapshots"] if s["snapshot_id"] == snapshot_id), None)

    @classmethod
    def _find_branch(cls, state: Dict[str, Any], branch_id: str) -> Optional[Dict[str, Any]]:
        return next((b for b in state["branches"] if b["branch_id"] == branch_id), None)

    @classmethod
    def _latest_snapshot_in_branch(cls, state: Dict[str, Any], branch_id: str) -> Optional[Dict[str, Any]]:
        snapshots = [s for s in state["snapshots"] if s["branch_id"] == branch_id]
        if not snapshots:
            return None
        snapshots.sort(key=lambda x: x["created_at"], reverse=True)
        return snapshots[0]

    @classmethod
    def _ensure_main_branch(cls, state: Dict[str, Any]) -> str:
        if state["branches"]:
            return state["branches"][0]["branch_id"]
        branch_id = f"branch_{uuid.uuid4().hex[:10]}"
        branch = {
            "branch_id": branch_id,
            "name": "main",
            "source_snapshot_id": None,
            "created_at": _now(),
            "updated_at": _now(),
            "status": "active",
            "score": None,
            "score_detail": None,
            "explanation": None
        }
        state["branches"].append(branch)
        return branch_id

    @classmethod
    def create_snapshot(
        cls,
        project_id: str,
        narrative_state: Dict[str, Any],
        title: Optional[str] = None,
        summary: Optional[str] = None,
        branch_id: Optional[str] = None,
        parent_snapshot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        state = cls.load(project_id)
        branch_id = branch_id or cls._ensure_main_branch(state)

        if not cls._find_branch(state, branch_id):
            raise ValueError(f"分支不存在: {branch_id}")
        if parent_snapshot_id and not cls._find_snapshot(state, parent_snapshot_id):
            raise ValueError(f"父快照不存在: {parent_snapshot_id}")

        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        snapshot = {
            "snapshot_id": snapshot_id,
            "branch_id": branch_id,
            "parent_snapshot_id": parent_snapshot_id,
            "title": title or "未命名快照",
            "summary": summary or "",
            "state": {
                "characters": narrative_state.get("characters", []),
                "events": narrative_state.get("events", []),
                "conflicts": narrative_state.get("conflicts", []),
                "goals": narrative_state.get("goals", []),
                "causal_links": narrative_state.get("causal_links", []),
                "timeline": narrative_state.get("timeline", []),
            },
            "created_at": _now(),
            "metadata": metadata or {}
        }
        state["snapshots"].append(snapshot)
        state["current_snapshot_id"] = snapshot_id

        branch = cls._find_branch(state, branch_id)
        branch["updated_at"] = _now()
        cls.save(project_id, state)
        return snapshot

    @classmethod
    def list_snapshots(cls, project_id: str, branch_id: Optional[str] = None) -> Dict[str, Any]:
        state = cls.load(project_id)
        snapshots = state["snapshots"]
        if branch_id:
            snapshots = [s for s in snapshots if s["branch_id"] == branch_id]
        snapshots.sort(key=lambda x: x["created_at"])
        return {
            "project_id": project_id,
            "current_snapshot_id": state.get("current_snapshot_id"),
            "selected_branch_id": state.get("selected_branch_id"),
            "branches": state["branches"],
            "snapshots": snapshots
        }

    @classmethod
    def rollback(cls, project_id: str, snapshot_id: str) -> Dict[str, Any]:
        state = cls.load(project_id)
        snapshot = cls._find_snapshot(state, snapshot_id)
        if not snapshot:
            raise ValueError(f"快照不存在: {snapshot_id}")
        state["current_snapshot_id"] = snapshot_id
        cls.save(project_id, state)
        return snapshot

    @classmethod
    def derive_branch(
        cls,
        project_id: str,
        from_snapshot_id: str,
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        state = cls.load(project_id)
        from_snapshot = cls._find_snapshot(state, from_snapshot_id)
        if not from_snapshot:
            raise ValueError(f"源快照不存在: {from_snapshot_id}")

        branch_id = f"branch_{uuid.uuid4().hex[:10]}"
        branch = {
            "branch_id": branch_id,
            "name": branch_name or f"branch-{len(state['branches']) + 1}",
            "source_snapshot_id": from_snapshot_id,
            "created_at": _now(),
            "updated_at": _now(),
            "status": "active",
            "score": None,
            "score_detail": None,
            "explanation": None
        }
        state["branches"].append(branch)

        snapshot = {
            "snapshot_id": f"snap_{uuid.uuid4().hex[:12]}",
            "branch_id": branch_id,
            "parent_snapshot_id": from_snapshot_id,
            "title": f"分支起点: {branch['name']}",
            "summary": "从已有剧情快照派生",
            "state": deepcopy(from_snapshot["state"]),
            "created_at": _now(),
            "metadata": {
                "derived_from_snapshot_id": from_snapshot_id
            }
        }
        state["snapshots"].append(snapshot)
        state["current_snapshot_id"] = snapshot["snapshot_id"]
        cls.save(project_id, state)
        return {
            "branch": branch,
            "snapshot": snapshot
        }

    @classmethod
    def advance_branch(
        cls,
        project_id: str,
        branch_id: str,
        state_patch: Optional[Dict[str, Any]] = None,
        delta_events: Optional[List[Dict[str, Any]]] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        state = cls.load(project_id)
        branch = cls._find_branch(state, branch_id)
        if not branch:
            raise ValueError(f"分支不存在: {branch_id}")

        latest = cls._latest_snapshot_in_branch(state, branch_id)
        if not latest:
            raise ValueError(f"分支没有可推进的起始快照: {branch_id}")

        next_state = deepcopy(latest["state"])
        patch = state_patch or {}
        for key in ["characters", "events", "conflicts", "goals", "causal_links", "timeline"]:
            if key in patch:
                next_state[key] = patch[key]

        if delta_events:
            next_state["events"] = (next_state.get("events", []) or []) + delta_events

        snapshot = {
            "snapshot_id": f"snap_{uuid.uuid4().hex[:12]}",
            "branch_id": branch_id,
            "parent_snapshot_id": latest["snapshot_id"],
            "title": title or "分支推进",
            "summary": summary or "",
            "state": next_state,
            "created_at": _now(),
            "metadata": {
                "advanced_from_snapshot_id": latest["snapshot_id"]
            }
        }
        state["snapshots"].append(snapshot)
        state["current_snapshot_id"] = snapshot["snapshot_id"]
        branch["updated_at"] = _now()
        cls.save(project_id, state)
        return snapshot

    @classmethod
    def _score_snapshot(cls, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        data = snapshot["state"]
        characters = data.get("characters", []) or []
        events = data.get("events", []) or []
        conflicts = data.get("conflicts", []) or []
        goals = data.get("goals", []) or []
        causal_links = data.get("causal_links", []) or []

        coherence = min(10.0, 4.0 + 0.6 * len(causal_links) + 0.2 * min(len(events), 10))
        character_consistency = min(10.0, 4.0 + 0.4 * len(characters) + 0.2 * len(goals))
        conflict_tension = min(10.0, 3.0 + 1.0 * min(len(conflicts), 6))
        watchability = min(10.0, 4.0 + 0.3 * len(events) + 0.4 * min(len(conflicts), 5))

        total = round(
            coherence * 0.3 +
            character_consistency * 0.25 +
            conflict_tension * 0.25 +
            watchability * 0.2, 2
        )

        explanation = (
            f"连贯性{coherence:.1f}（因果链{len(causal_links)}，事件{len(events)}），"
            f"角色一致性{character_consistency:.1f}（角色{len(characters)}，目标{len(goals)}），"
            f"冲突张力{conflict_tension:.1f}（冲突{len(conflicts)}），"
            f"观赏性{watchability:.1f}（事件与冲突强度综合）。"
        )

        return {
            "coherence": round(coherence, 2),
            "character_consistency": round(character_consistency, 2),
            "conflict_tension": round(conflict_tension, 2),
            "watchability": round(watchability, 2),
            "total": total,
            "explanation": explanation
        }

    @classmethod
    def score_branches(cls, project_id: str) -> List[Dict[str, Any]]:
        state = cls.load(project_id)
        ranked: List[Dict[str, Any]] = []
        for branch in state["branches"]:
            latest = cls._latest_snapshot_in_branch(state, branch["branch_id"])
            if not latest:
                continue
            score = cls._score_snapshot(latest)
            branch["score"] = score["total"]
            branch["score_detail"] = {
                "coherence": score["coherence"],
                "character_consistency": score["character_consistency"],
                "conflict_tension": score["conflict_tension"],
                "watchability": score["watchability"]
            }
            branch["explanation"] = score["explanation"]
            branch["updated_at"] = _now()
            ranked.append({
                "branch_id": branch["branch_id"],
                "name": branch["name"],
                "latest_snapshot_id": latest["snapshot_id"],
                "score": score["total"],
                "score_detail": branch["score_detail"],
                "explanation": branch["explanation"]
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        cls.save(project_id, state)
        return ranked

    @classmethod
    def select_branch(cls, project_id: str, branch_id: str) -> Dict[str, Any]:
        state = cls.load(project_id)
        branch = cls._find_branch(state, branch_id)
        if not branch:
            raise ValueError(f"分支不存在: {branch_id}")
        state["selected_branch_id"] = branch_id
        cls.save(project_id, state)
        return branch

    @classmethod
    def export_script(cls, project_id: str, branch_id: Optional[str] = None) -> Dict[str, Any]:
        state = cls.load(project_id)
        target_branch_id = branch_id or state.get("selected_branch_id")
        if not target_branch_id:
            raise ValueError("未指定分支，且尚未选择默认结局分支")

        branch = cls._find_branch(state, target_branch_id)
        if not branch:
            raise ValueError(f"分支不存在: {target_branch_id}")

        snapshots = [s for s in state["snapshots"] if s["branch_id"] == target_branch_id]
        snapshots.sort(key=lambda x: x["created_at"])
        if not snapshots:
            raise ValueError("目标分支无快照，无法导出")

        latest = snapshots[-1]
        score_detail = branch.get("score_detail") or {}
        explanation = branch.get("explanation") or "该分支已被选定为候选结局。"

        return {
            "project_id": project_id,
            "branch": {
                "branch_id": branch["branch_id"],
                "name": branch["name"],
                "score": branch.get("score"),
                "score_detail": score_detail,
                "explanation": explanation
            },
            "script": {
                "title": f"《{branch['name']}》结局稿",
                "logline": latest.get("summary", ""),
                "characters": latest["state"].get("characters", []),
                "events": latest["state"].get("events", []),
                "conflicts": latest["state"].get("conflicts", []),
                "goals": latest["state"].get("goals", []),
                "causal_links": latest["state"].get("causal_links", []),
                "timeline": latest["state"].get("timeline", []),
                "snapshot_chain": [
                    {
                        "snapshot_id": s["snapshot_id"],
                        "title": s.get("title"),
                        "summary": s.get("summary"),
                        "created_at": s.get("created_at")
                    }
                    for s in snapshots
                ]
            }
        }

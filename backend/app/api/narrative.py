"""
影视叙事结局推理 API
最小闭环：快照、分支、评分、导出
"""

from flask import jsonify, request

from . import narrative_bp
from ..services.narrative_manager import NarrativeManager
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.narrative")


def _json_body():
    return request.get_json(silent=True) or {}


@narrative_bp.route("/state/<project_id>", methods=["GET"])
def get_narrative_state(project_id: str):
    try:
        branch_id = request.args.get("branch_id")
        data = NarrativeManager.list_snapshots(project_id, branch_id=branch_id)
        return jsonify({"success": True, "data": data})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"获取叙事状态失败: {e}")
        return jsonify({"success": False, "error": "获取叙事状态失败"}), 500


@narrative_bp.route("/snapshot", methods=["POST"])
def create_snapshot():
    try:
        data = _json_body()
        project_id = data.get("project_id")
        narrative_state = data.get("narrative_state") or {}
        if not project_id:
            return jsonify({"success": False, "error": "缺少 project_id"}), 400

        snapshot = NarrativeManager.create_snapshot(
            project_id=project_id,
            narrative_state=narrative_state,
            title=data.get("title"),
            summary=data.get("summary"),
            branch_id=data.get("branch_id"),
            parent_snapshot_id=data.get("parent_snapshot_id"),
            metadata=data.get("metadata"),
        )
        return jsonify({"success": True, "data": snapshot})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"创建快照失败: {e}")
        return jsonify({"success": False, "error": "创建快照失败"}), 500


@narrative_bp.route("/rollback", methods=["POST"])
def rollback_snapshot():
    try:
        data = _json_body()
        project_id = data.get("project_id")
        snapshot_id = data.get("snapshot_id")
        if not project_id or not snapshot_id:
            return jsonify({"success": False, "error": "缺少 project_id 或 snapshot_id"}), 400

        snapshot = NarrativeManager.rollback(project_id, snapshot_id)
        return jsonify({"success": True, "data": snapshot})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"回滚快照失败: {e}")
        return jsonify({"success": False, "error": "回滚快照失败"}), 500


@narrative_bp.route("/branch/derive", methods=["POST"])
def derive_branch():
    try:
        data = _json_body()
        project_id = data.get("project_id")
        from_snapshot_id = data.get("from_snapshot_id")
        if not project_id or not from_snapshot_id:
            return jsonify({"success": False, "error": "缺少 project_id 或 from_snapshot_id"}), 400

        result = NarrativeManager.derive_branch(
            project_id=project_id,
            from_snapshot_id=from_snapshot_id,
            branch_name=data.get("branch_name"),
        )
        return jsonify({"success": True, "data": result})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"派生分支失败: {e}")
        return jsonify({"success": False, "error": "派生分支失败"}), 500


@narrative_bp.route("/branch/advance", methods=["POST"])
def advance_branch():
    try:
        data = _json_body()
        project_id = data.get("project_id")
        branch_id = data.get("branch_id")
        if not project_id or not branch_id:
            return jsonify({"success": False, "error": "缺少 project_id 或 branch_id"}), 400

        snapshot = NarrativeManager.advance_branch(
            project_id=project_id,
            branch_id=branch_id,
            state_patch=data.get("state_patch"),
            delta_events=data.get("delta_events"),
            title=data.get("title"),
            summary=data.get("summary"),
        )
        return jsonify({"success": True, "data": snapshot})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"推进分支失败: {e}")
        return jsonify({"success": False, "error": "推进分支失败"}), 500


@narrative_bp.route("/branches/score", methods=["POST"])
def score_branches():
    try:
        data = _json_body()
        project_id = data.get("project_id")
        if not project_id:
            return jsonify({"success": False, "error": "缺少 project_id"}), 400

        ranking = NarrativeManager.score_branches(project_id)
        return jsonify({"success": True, "data": ranking})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"分支评分失败: {e}")
        return jsonify({"success": False, "error": "分支评分失败"}), 500


@narrative_bp.route("/ending/select", methods=["POST"])
def select_ending():
    try:
        data = _json_body()
        project_id = data.get("project_id")
        branch_id = data.get("branch_id")
        if not project_id or not branch_id:
            return jsonify({"success": False, "error": "缺少 project_id 或 branch_id"}), 400

        branch = NarrativeManager.select_branch(project_id, branch_id)
        return jsonify({"success": True, "data": branch})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"选择结局失败: {e}")
        return jsonify({"success": False, "error": "选择结局失败"}), 500


@narrative_bp.route("/export/<project_id>", methods=["GET"])
def export_script(project_id: str):
    try:
        branch_id = request.args.get("branch_id")
        result = NarrativeManager.export_script(project_id=project_id, branch_id=branch_id)
        return jsonify({"success": True, "data": result})
    except ValueError:
        return jsonify({"success": False, "error": "请求参数不合法"}), 400
    except Exception as e:
        logger.error(f"导出剧本失败: {e}")
        return jsonify({"success": False, "error": "导出剧本失败"}), 500

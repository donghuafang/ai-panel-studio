import asyncio
import json
import threading
from datetime import datetime, timezone

from backend.app.models import Discussion, Guest, Speech, Consensus, Divergence
from backend.app.services.llm_client import LLMClient


class DiscussionOrchestrator:
    """讨论编排引擎：管理 SSE 事件广播 + 后台自动推进讨论"""

    def __init__(self):
        # discussion_id -> list[asyncio.Queue]
        self._event_queues: dict[str, list[asyncio.Queue]] = {}
        self._lock = threading.Lock()

    def subscribe(self, discussion_id: str) -> asyncio.Queue:
        """注册 SSE 客户端，返回其专属事件队列"""
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            if discussion_id not in self._event_queues:
                self._event_queues[discussion_id] = []
            self._event_queues[discussion_id].append(q)
        return q

    def unsubscribe(self, discussion_id: str, queue: asyncio.Queue):
        """取消注册 SSE 客户端"""
        with self._lock:
            queues = self._event_queues.get(discussion_id, [])
            if queue in queues:
                queues.remove(queue)

    def _broadcast(self, discussion_id: str, event: str, data: dict):
        """向所有订阅者广播 SSE 事件（线程安全）"""
        with self._lock:
            queues = list(self._event_queues.get(discussion_id, []))
        payload = json.dumps(data, ensure_ascii=False)
        for q in queues:
            try:
                q.put_nowait({"event": event, "data": payload})
            except asyncio.QueueFull:
                pass

    def _build_context(self, speeches: list[Speech], guests: dict[str, Guest]) -> list[dict]:
        """用已有发言构建 LLM 上下文消息列表"""
        messages = []
        for s in speeches:
            guest = guests.get(s.guest_id) if s.guest_id else None
            name = guest.name if guest else "未知嘉宾"
            messages.append({
                "role": "user",
                "content": f"【{name}】({s.speech_type}): {s.content}",
            })
        return messages

    def run_discussion(self, session_factory, discussion_id: str):
        """在后台线程中运行全自动讨论（同步数据库操作）"""
        import time

        llm = LLMClient()
        db = session_factory()

        try:
            discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
            if not discussion or discussion.status != "active":
                return

            guests = db.query(Guest).filter(Guest.discussion_id == discussion_id).all()
            guest_map = {g.id: g for g in guests}
            host = next((g for g in guests if g.role == "host"), None)
            experts = [g for g in guests if g.role == "guest"]

            all_speeches: list[Speech] = []

            for round_num in range(1, discussion.max_rounds + 1):
                # 更新当前轮次
                discussion.current_round = round_num
                db.commit()

                # ── 主持人开场/引导 ──
                if host:
                    self._set_agent_state(db, host, "thinking")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": host.id, "agent_state": "thinking"
                    })

                    if round_num == 1:
                        purpose = f"作为主持人，请你围绕「{discussion.topic}」做开场白，简要介绍话题背景，并引导各位专家依次发表观点。"
                    else:
                        purpose = f"第 {round_num} 轮开始。请基于前面的讨论，提炼关键争议点，引导专家们深入辩论或回应之前的观点。"
                    context = self._build_context(all_speeches, guest_map)
                    content = asyncio.run(llm.generate_speech(
                        host.name, host.stance, "host", context, purpose
                    ))

                    self._set_agent_state(db, host, "speaking")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": host.id, "agent_state": "speaking"
                    })

                    speech = self._save_speech(db, discussion_id, host.id, round_num, content,
                                               "question" if round_num > 1 else "statement")
                    all_speeches.append(speech)
                    event_data = self._speech_to_event(speech)
                    self._broadcast(discussion_id, "speech_added", event_data)

                    self._set_agent_state(db, host, "ready")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": host.id, "agent_state": "ready"
                    })

                    time.sleep(0.5)  # 短暂间隔让前端有时间渲染

                # ── 专家依次发言 ──
                for expert in experts:
                    self._set_agent_state(db, expert, "thinking")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": expert.id, "agent_state": "thinking"
                    })

                    purpose = f"第 {round_num} 轮发言。请基于讨论话题「{discussion.topic}」和之前的讨论内容，发表你的专业观点。保持与你的立场（{expert.stance}）一致。"
                    context = self._build_context(all_speeches, guest_map)
                    content = asyncio.run(llm.generate_speech(
                        expert.name, expert.stance, "guest", context, purpose
                    ))

                    self._set_agent_state(db, expert, "speaking")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": expert.id, "agent_state": "speaking"
                    })

                    speech = self._save_speech(db, discussion_id, expert.id, round_num, content, "statement")
                    all_speeches.append(speech)
                    event_data = self._speech_to_event(speech)
                    self._broadcast(discussion_id, "speech_added", event_data)

                    self._set_agent_state(db, expert, "ready")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": expert.id, "agent_state": "ready"
                    })

                    time.sleep(0.5)

                # ── 主持人本轮小结 ──
                if host:
                    self._set_agent_state(db, host, "thinking")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": host.id, "agent_state": "thinking"
                    })

                    purpose = f"第 {round_num} 轮即将结束。请对刚才各位专家的发言做一个简要小结，提炼关键观点和共识/分歧线索。"
                    context = self._build_context(all_speeches, guest_map)
                    content = asyncio.run(llm.generate_speech(
                        host.name, host.stance, "host", context, purpose
                    ))

                    self._set_agent_state(db, host, "speaking")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": host.id, "agent_state": "speaking"
                    })

                    speech = self._save_speech(db, discussion_id, host.id, round_num, content, "summary")
                    all_speeches.append(speech)
                    event_data = self._speech_to_event(speech)
                    self._broadcast(discussion_id, "speech_added", event_data)

                    self._set_agent_state(db, host, "ready")
                    self._broadcast(discussion_id, "guest_state_changed", {
                        "guest_id": host.id, "agent_state": "ready"
                    })

                    time.sleep(0.5)

            # ── 全部轮次结束：生成共识与分歧 ──
            if host:
                self._generate_summary(db, llm, discussion_id, host, guests, all_speeches, guest_map)

            # ── 标记讨论结束 ──
            discussion.status = "ended"
            db.commit()

            final_consensus = [
                {
                    "id": c.id, "discussion_id": c.discussion_id, "content": c.content,
                    "supporter_guest_ids": c.supporter_guest_ids,
                    "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat(),
                }
                for c in db.query(Consensus).filter(Consensus.discussion_id == discussion_id).all()
            ]
            final_divergence = [
                {
                    "id": d.id, "discussion_id": d.discussion_id, "content": d.content,
                    "opposing_pairs": d.opposing_pairs,
                    "created_at": d.created_at.isoformat(), "updated_at": d.updated_at.isoformat(),
                }
                for d in db.query(Divergence).filter(Divergence.discussion_id == discussion_id).all()
            ]
            self._broadcast(discussion_id, "discussion_ended", {
                "discussion_id": discussion_id,
                "final_consensus": final_consensus,
                "final_divergence": final_divergence,
            })

        except Exception as e:
            db.rollback()
            try:
                discussion.status = "error"
                db.commit()
            except Exception:
                pass  # Best-effort: DB may be unavailable
            self._broadcast(discussion_id, "error", {"code": "ORCHESTRATION_ERROR", "message": str(e)})
        finally:
            db.close()

    def _set_agent_state(self, db, guest: Guest, state: str):
        guest.agent_state = state
        db.commit()
        db.refresh(guest)

    def _save_speech(self, db, discussion_id: str, guest_id: str, round_num: int, content: str, speech_type: str) -> Speech:
        speech = Speech(
            discussion_id=discussion_id,
            guest_id=guest_id,
            round_number=round_num,
            content=content,
            speech_type=speech_type,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(speech)
        db.commit()
        db.refresh(speech)
        return speech

    def _speech_to_event(self, speech: Speech) -> dict:
        return {
            "speech": {
                "id": speech.id,
                "discussion_id": speech.discussion_id,
                "guest_id": speech.guest_id,
                "round_number": speech.round_number,
                "content": speech.content,
                "speech_type": speech.speech_type,
                "timestamp": speech.timestamp.isoformat(),
            },
            "round_number": speech.round_number,
        }

    def _generate_summary(self, db, llm: LLMClient, discussion_id: str, host: Guest,
                          guests: list[Guest], all_speeches: list[Speech], guest_map: dict):
        """生成共识与分歧总结"""
        context = self._build_context(all_speeches, guest_map)
        expert_names = ", ".join([g.name for g in guests if g.role == "guest"])

        summary_prompt = f"""讨论已结束。请基于以上全部发言内容，总结出：

1. 共识（至少1条）：嘉宾们达成一致的要点，并标明哪些嘉宾支持该共识
2. 分歧（至少1条）：嘉宾们存在争议的要点，并标明对立双方的嘉宾姓名对

返回严格的 JSON 格式（不要 markdown 代码块）：
{{
  "consensus_list": [
    {{ "content": "共识内容", "supporter_names": ["张三", "李四"] }}
  ],
  "divergence_list": [
    {{ "content": "分歧描述", "opposing_names": [["张三", "李四"]] }}
  ]
}}

注意：supporter_names 和 opposing_names 中使用嘉宾的姓名（从上下文消息中的【姓名】格式获取）。
可供参考的嘉宾名单：主持人 {host.name}，专家：{expert_names}"""

        messages = context + [{"role": "user", "content": summary_prompt}]
        raw = asyncio.run(llm.chat_completion(messages, temperature=0.5))
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)

        import json as _json
        try:
            result = _json.loads(raw)

            # 名字到 ID 的映射
            name_to_id = {g.name: g.id for g in guests}

            # 保存共识
            for c in result.get("consensus_list", []):
                supporter_ids = [name_to_id.get(n, "") for n in c.get("supporter_names", [])]
                supporter_ids = [sid for sid in supporter_ids if sid]
                consensus = Consensus(
                    discussion_id=discussion_id,
                    content=c["content"],
                    supporter_guest_ids=supporter_ids,
                )
                db.add(consensus)
                db.commit()
                db.refresh(consensus)
                self._broadcast(discussion_id, "consensus_updated", {
                    "consensus": {
                        "id": consensus.id, "discussion_id": consensus.discussion_id,
                        "content": consensus.content, "supporter_guest_ids": consensus.supporter_guest_ids,
                        "created_at": consensus.created_at.isoformat(), "updated_at": consensus.updated_at.isoformat(),
                    }
                })

            # 保存分歧
            for d in result.get("divergence_list", []):
                opposing_pairs = []
                for pair in d.get("opposing_names", []):
                    id_pair = [name_to_id.get(n, "") for n in pair]
                    id_pair = [i for i in id_pair if i]
                    if len(id_pair) == 2:
                        opposing_pairs.append(id_pair)
                divergence = Divergence(
                    discussion_id=discussion_id,
                    content=d["content"],
                    opposing_pairs=opposing_pairs,
                )
                db.add(divergence)
                db.commit()
                db.refresh(divergence)
                self._broadcast(discussion_id, "divergence_updated", {
                    "divergence": {
                        "id": divergence.id, "discussion_id": divergence.discussion_id,
                        "content": divergence.content, "opposing_pairs": divergence.opposing_pairs,
                        "created_at": divergence.created_at.isoformat(), "updated_at": divergence.updated_at.isoformat(),
                    }
                })
        except Exception:
            pass  # Summary generation is best-effort; discussion still ends


# 全局单例
orchestrator = DiscussionOrchestrator()
